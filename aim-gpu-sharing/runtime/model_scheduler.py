"""
Model Scheduler for Multi-Model Deployment

This module provides scheduling logic for managing multiple model instances
on a partitioned GPU.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# Handle both relative and absolute imports
try:
    from .rocm_partitioner import ROCmPartitioner
    from .rocm_partitioner_real import ROCmPartitionerReal
    from .model_sizing import ModelSizingConfig
    from .hardware_detector import get_partitioner_class, HardwareCapability
except ImportError:
    from rocm_partitioner import ROCmPartitioner
    try:
        from rocm_partitioner_real import ROCmPartitionerReal
    except ImportError:
        ROCmPartitionerReal = None
    from model_sizing import ModelSizingConfig
    from hardware_detector import get_partitioner_class, HardwareCapability

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ModelInstance:
    """Represents a model instance on a partition."""
    model_id: str
    partition_id: int
    status: ModelStatus
    memory_allocated_gb: float
    priority: int  # Higher number = higher priority


class ModelScheduler:
    """
    Scheduler for managing multiple model instances on partitioned GPU.
    
    This class handles allocation, scheduling, and lifecycle management
    of multiple models sharing GPU resources.
    
    Works with both simulation and real hardware partitioners.
    """
    
    def __init__(
        self,
        partitioner: Optional[Union[ROCmPartitioner, 'ROCmPartitionerReal']] = None,
        gpu_id: int = 0,
        config_path: Optional[str] = None,
        auto_detect: bool = True
    ):
        """
        Initialize model scheduler.
        
        Args:
            partitioner: ROCmPartitioner instance (optional if auto_detect=True)
            gpu_id: GPU device ID (used if auto_detect=True)
            config_path: Path to model sizing configuration
            auto_detect: Automatically detect hardware and select partitioner
        """
        self.sizing_config = ModelSizingConfig(config_path)
        self.models: Dict[str, ModelInstance] = {}
        self.partition_assignments: Dict[int, List[str]] = {}
        
        # Auto-detect hardware if requested
        if auto_detect and partitioner is None:
            partitioner_class, capability, info = get_partitioner_class(gpu_id)
            if capability == HardwareCapability.REAL_PARTITIONING:
                # Initialize real partitioner with recommended settings
                partitioner = partitioner_class(gpu_id=gpu_id, config_path=config_path)
                # Use CPX/NPS4 for multi-model deployment
                from rocm_partitioner_real import (
                    ComputePartitionMode,
                    MemoryPartitionMode
                )
                success = partitioner.initialize(
                    gpu_name=info.model_name or "MI300X",
                    compute_mode=ComputePartitionMode.CPX,
                    memory_mode=MemoryPartitionMode.NPS4
                )
                if not success:
                    logger.warning(
                        "Failed to initialize real partitions, "
                        "partitioner may need manual initialization"
                    )
            else:
                # Use simulation partitioner
                partitioner = partitioner_class(gpu_id=gpu_id, config_path=config_path)
        
        if partitioner is None:
            raise ValueError("Partitioner is required")
        
        self.partitioner = partitioner
        self.hardware_capability = getattr(partitioner, 'amd_smi_available', False)
    
    def schedule_model(
        self,
        model_id: str,
        priority: int = 0,
        preferred_partition: Optional[int] = None,
        precision: str = "fp16"
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Schedule a model for deployment.
        
        Args:
            model_id: Model identifier
            priority: Model priority (higher = more important)
            preferred_partition: Preferred partition ID (optional)
            precision: Model precision (fp16, int8, int4)
        
        Returns:
            Tuple of (success, partition_id, error_message)
        """
        # Check if model already scheduled
        if model_id in self.models:
            instance = self.models[model_id]
            if instance.status == ModelStatus.RUNNING:
                return True, instance.partition_id, None
            elif instance.status == ModelStatus.SCHEDULED:
                return True, instance.partition_id, "Already scheduled"
        
        # Find suitable partition
        partition_id = self._find_suitable_partition(
            model_id,
            preferred_partition,
            precision=precision
        )
        
        if partition_id is None:
            return False, None, "No suitable partition available"
        
        # Allocate model to partition
        # Handle both simulation and real partitioners
        if hasattr(self.partitioner, 'allocate_model'):
            # Real partitioner supports precision parameter
            if 'precision' in self.partitioner.allocate_model.__code__.co_varnames:
                success, error = self.partitioner.allocate_model(
                    model_id, partition_id, precision=precision
                )
            else:
                # Simulation partitioner
                success, error = self.partitioner.allocate_model(model_id, partition_id)
        else:
            return False, None, "Partitioner does not support model allocation"
        
        if not success:
            return False, None, error
        
        # Create model instance
        model_size = self.sizing_config.estimate_model_size(
            model_id,
            precision=precision
        )
        instance = ModelInstance(
            model_id=model_id,
            partition_id=partition_id,
            status=ModelStatus.SCHEDULED,
            memory_allocated_gb=model_size,
            priority=priority,
        )
        
        self.models[model_id] = instance
        
        # Update partition assignments
        if partition_id not in self.partition_assignments:
            self.partition_assignments[partition_id] = []
        self.partition_assignments[partition_id].append(model_id)
        
        logger.info(
            f"Scheduled model {model_id} ({precision}) on partition {partition_id} "
            f"(priority: {priority}, {model_size:.1f}GB)"
        )
        
        return True, partition_id, None
    
    def _find_suitable_partition(
        self,
        model_id: str,
        preferred_partition: Optional[int] = None,
        precision: str = "fp16"
    ) -> Optional[int]:
        """
        Find a suitable partition for a model.
        
        Args:
            model_id: Model identifier
            preferred_partition: Preferred partition ID
            precision: Model precision (fp16, int8, int4)
        
        Returns:
            Partition ID if found, None otherwise
        """
        model_size = self.sizing_config.estimate_model_size(
            model_id,
            precision=precision
        )
        
        # Check preferred partition first
        if preferred_partition is not None:
            partition = self.partitioner.get_partition_info(preferred_partition)
            if partition:
                available = (
                    (partition.size_bytes - partition.allocated_bytes) / (1024 ** 3)
                )
                if model_size <= available:
                    return preferred_partition
        
        # Find best available partition
        # Handle both simulation and real partitioners
        if hasattr(self.partitioner, 'get_available_partitions'):
            available_partitions = self.partitioner.get_available_partitions()
        elif hasattr(self.partitioner, 'get_logical_devices'):
            # Real partitioner - get all logical devices
            devices = self.partitioner.get_logical_devices()
            available_partitions = [d['device_id'] for d in devices]
        else:
            # Fallback: try to get partitions from internal structure
            available_partitions = list(self.partitioner.partitions.keys())
        
        # Sort by available space (largest first)
        partition_sizes = []
        for partition_id in available_partitions:
            partition = self.partitioner.get_partition_info(partition_id)
            if partition:
                available = (
                    (partition.size_bytes - partition.allocated_bytes) / (1024 ** 3)
                )
                partition_sizes.append((partition_id, available))
        
        partition_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Find first partition that fits
        for partition_id, available in partition_sizes:
            if model_size <= available:
                return partition_id
        
        return None
    
    def unschedule_model(self, model_id: str) -> bool:
        """
        Unschedule and remove a model.
        
        Args:
            model_id: Model identifier
        
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        instance = self.models[model_id]
        partition_id = instance.partition_id
        
        # Deallocate from partitioner
        success = self.partitioner.deallocate_model(model_id, partition_id)
        if not success:
            logger.error(f"Failed to deallocate model {model_id}")
            return False
        
        # Remove from assignments
        if partition_id in self.partition_assignments:
            if model_id in self.partition_assignments[partition_id]:
                self.partition_assignments[partition_id].remove(model_id)
        
        # Remove model instance
        del self.models[model_id]
        
        logger.info(f"Unscheduled model {model_id}")
        return True
    
    def update_model_status(
        self,
        model_id: str,
        status: ModelStatus
    ) -> bool:
        """
        Update model status.
        
        Args:
            model_id: Model identifier
            status: New status
        
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.models:
            return False
        
        self.models[model_id].status = status
        logger.debug(f"Updated {model_id} status to {status.value}")
        return True
    
    def get_model_info(self, model_id: str) -> Optional[ModelInstance]:
        """Get information about a scheduled model."""
        return self.models.get(model_id)
    
    def get_partition_models(self, partition_id: int) -> List[str]:
        """Get list of models on a partition."""
        return self.partition_assignments.get(partition_id, [])
    
    def get_partition_environment(self, partition_id: int) -> Dict[str, str]:
        """
        Get environment variables for a partition.
        
        Works with both simulation and real partitioners.
        
        Args:
            partition_id: Partition ID
        
        Returns:
            Dictionary of environment variables
        """
        if hasattr(self.partitioner, 'get_environment_variables'):
            return self.partitioner.get_environment_variables(partition_id)
        else:
            # Fallback for simulation partitioner
            return {
                'ROCR_VISIBLE_DEVICES': str(self.partitioner.gpu_id),
                'AIM_PARTITION_ID': str(partition_id)
            }
    
    def get_scheduled_models(self) -> List[str]:
        """Get list of all scheduled model IDs."""
        return list(self.models.keys())
    
    def get_running_models(self) -> List[str]:
        """Get list of running model IDs."""
        return [
            model_id
            for model_id, instance in self.models.items()
            if instance.status == ModelStatus.RUNNING
        ]
    
    def validate_schedule(self) -> Tuple[bool, List[str]]:
        """
        Validate current schedule.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate partitioner
        is_valid, partition_errors = self.partitioner.validate_partitioning()
        if not is_valid:
            errors.extend(partition_errors)
        
        # Validate model assignments
        for model_id, instance in self.models.items():
            partition = self.partitioner.get_partition_info(instance.partition_id)
            if not partition:
                errors.append(
                    f"Model {model_id} assigned to non-existent partition "
                    f"{instance.partition_id}"
                )
            elif model_id not in partition.models:
                errors.append(
                    f"Model {model_id} not found in partition "
                    f"{instance.partition_id}"
                )
        
        return len(errors) == 0, errors

