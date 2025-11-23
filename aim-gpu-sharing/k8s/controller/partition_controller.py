"""
Kubernetes Partition Controller for GPU Sharing

This controller watches InferenceService CRs and manages GPU partition allocation
using the ROCm partitioner.
"""

import os
import logging
import sys
from typing import Dict, Optional
from datetime import datetime
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# Add runtime to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../runtime'))

from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
from model_scheduler import ModelScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartitionController:
    """Kubernetes controller for managing GPU partitions."""
    
    def __init__(self, gpu_id: int = 0, namespace: Optional[str] = None):
        """
        Initialize partition controller.
        
        Args:
            gpu_id: GPU device ID
            namespace: Kubernetes namespace to watch (None for all namespaces)
        """
        self.gpu_id = gpu_id
        self.namespace = namespace or os.getenv('NAMESPACE', 'default')
        
        # Initialize K8s client
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except:
            try:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes config")
            except Exception as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                raise
        
        self.api = client.CustomObjectsApi()
        self.core_api = client.CoreV1Api()
        
        # Initialize partitioner and scheduler
        self.partitioner = ROCmPartitionerReal(gpu_id=gpu_id)
        if not self.partitioner.amd_smi_available:
            raise RuntimeError("amd-smi not available - cannot use real partitioner")
        
        # Get current partition modes and initialize
        compute, memory = self.partitioner.get_current_partition_mode()
        compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
        memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
        
        if not self.partitioner.initialize("MI300X", compute_mode, memory_mode):
            raise RuntimeError("Failed to initialize partitioner")
        
        self.scheduler = ModelScheduler(partitioner=self.partitioner, gpu_id=gpu_id)
        
        logger.info(f"Partition controller initialized: GPU {gpu_id}, {len(self.partitioner.partitions)} partitions")
    
    def _get_gpu_sharing_config(self, spec: Dict) -> Optional[Dict]:
        """Extract GPU sharing configuration from InferenceService spec."""
        return spec.get('gpuSharing')
    
    def _should_manage(self, gpu_config: Dict) -> bool:
        """Check if this controller should manage this service."""
        return gpu_config and gpu_config.get('enabled', False)
    
    def _schedule_model(self, name: str, gpu_config: Dict) -> Optional[Dict]:
        """
        Schedule a model to a partition.
        
        Returns:
            Partition info dict or None if scheduling failed
        """
        try:
            # Get model size from config or use default
            memory_gb = gpu_config.get('memoryLimitGB', 20.0)
            
            # Schedule model
            success, partition_id, error = self.scheduler.schedule_model(
                model_id=name,
                memory_gb=memory_gb,
                preferred_partition=gpu_config.get('preferredPartition'),
                priority=gpu_config.get('qosPriority', 'medium')
            )
            
            if not success:
                logger.error(f"Failed to schedule model {name}: {error}")
                return None
            
            # Get partition info
            partition = self.partitioner.partitions.get(partition_id)
            if not partition:
                logger.error(f"Partition {partition_id} not found")
                return None
            
            return {
                'partitionId': partition_id,
                'computeMode': self.partitioner.compute_mode.value if self.partitioner.compute_mode else 'SPX',
                'memoryMode': self.partitioner.memory_mode.value if self.partitioner.memory_mode else 'NPS1',
                'partitionSizeGB': partition.size_bytes / (1024 ** 3),
                'allocatedMemoryGB': partition.allocated_bytes / (1024 ** 3),
                'availableMemoryGB': (partition.size_bytes - partition.allocated_bytes) / (1024 ** 3)
            }
        except Exception as e:
            logger.error(f"Error scheduling model {name}: {e}")
            return None
    
    def _unschedule_model(self, name: str):
        """Unschedule a model from its partition."""
        try:
            self.scheduler.unschedule_model(name)
        except Exception as e:
            logger.error(f"Error unscheduling model {name}: {e}")
    
    def _update_status(self, name: str, namespace: str, partition_info: Optional[Dict], 
                      condition_type: str, condition_status: str, reason: str, message: str):
        """Update InferenceService status."""
        try:
            status = {
                'partitionInfo': partition_info,
                'conditions': [{
                    'type': condition_type,
                    'status': condition_status,
                    'reason': reason,
                    'message': message,
                    'lastTransitionTime': datetime.utcnow().isoformat() + 'Z'
                }]
            }
            
            # Get current resource
            try:
                resource = self.api.get_namespaced_custom_object(
                    group='aim.amd.com',
                    version='v1alpha1',
                    namespace=namespace,
                    plural='inferenceservices',
                    name=name
                )
            except ApiException as e:
                if e.status == 404:
                    logger.warning(f"InferenceService {name} not found")
                    return
                raise
            
            # Update status
            resource['status'] = status
            self.api.patch_namespaced_custom_object_status(
                group='aim.amd.com',
                version='v1alpha1',
                namespace=namespace,
                plural='inferenceservices',
                name=name,
                body=resource
            )
            
            logger.info(f"Updated status for {name}: {condition_type}={condition_status}")
        except Exception as e:
            logger.error(f"Error updating status for {name}: {e}")
    
    def reconcile(self, name: str, namespace: str, spec: Dict):
        """
        Reconcile an InferenceService.
        
        Args:
            name: InferenceService name
            namespace: Namespace
            spec: InferenceService spec
        """
        logger.info(f"Reconciling InferenceService {namespace}/{name}")
        
        gpu_config = self._get_gpu_sharing_config(spec)
        
        if not self._should_manage(gpu_config):
            logger.debug(f"Skipping {name} - GPU sharing not enabled")
            return
        
        # Schedule model
        partition_info = self._schedule_model(name, gpu_config)
        
        if partition_info:
            self._update_status(
                name, namespace, partition_info,
                'PartitionAllocated', 'True', 'Scheduled',
                f"Model scheduled to partition {partition_info['partitionId']}"
            )
        else:
            self._update_status(
                name, namespace, None,
                'PartitionAllocated', 'False', 'SchedulingFailed',
                'Failed to allocate partition for model'
            )
    
    def handle_delete(self, name: str, namespace: str):
        """Handle InferenceService deletion."""
        logger.info(f"Handling deletion of InferenceService {namespace}/{name}")
        self._unschedule_model(name)
    
    def run(self):
        """Run the controller watch loop."""
        logger.info(f"Starting partition controller (namespace: {self.namespace})")
        
        w = watch.Watch()
        
        try:
            for event in w.stream(
                self.api.list_cluster_custom_object,
                group='aim.amd.com',
                version='v1alpha1',
                plural='inferenceservices',
                watch=True
            ):
                obj = event['object']
                event_type = event['type']
                name = obj['metadata']['name']
                namespace = obj['metadata'].get('namespace', 'default')
                
                # Filter by namespace if specified
                if self.namespace != 'default' and namespace != self.namespace:
                    continue
                
                if event_type == 'ADDED' or event_type == 'MODIFIED':
                    spec = obj.get('spec', {})
                    self.reconcile(name, namespace, spec)
                elif event_type == 'DELETED':
                    self.handle_delete(name, namespace)
        except KeyboardInterrupt:
            logger.info("Controller stopped by user")
        except Exception as e:
            logger.error(f"Error in watch loop: {e}")
            raise


def main():
    """Main entry point for controller."""
    gpu_id = int(os.getenv('GPU_ID', '0'))
    namespace = os.getenv('NAMESPACE', None)
    
    controller = PartitionController(gpu_id=gpu_id, namespace=namespace)
    controller.run()


if __name__ == '__main__':
    main()

