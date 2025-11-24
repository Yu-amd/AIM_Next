"""
Kubernetes controller for FineTuningJob CRD.

Manages the lifecycle of fine-tuning jobs in Kubernetes.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FineTuningJobController:
    """Controller for managing FineTuningJob resources."""
    
    def __init__(self, namespace: str = "default"):
        """
        Initialize the controller.
        
        Args:
            namespace: Kubernetes namespace to watch
        """
        self.namespace = namespace
        
        # Load Kubernetes config
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
        
        # Create API clients
        self.api = client.CustomObjectsApi()
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        
        # CRD details
        self.group = "aim.amd.com"
        self.version = "v1alpha1"
        self.plural = "finetuningjobs"
    
    def update_status(
        self,
        name: str,
        status: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> None:
        """
        Update FineTuningJob status.
        
        Args:
            name: Job name
            status: Status dictionary
            namespace: Optional namespace (uses self.namespace if not provided)
        """
        namespace = namespace or self.namespace
        
        try:
            # Get current resource
            resource = self.api.get_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace=namespace,
                plural=self.plural,
                name=name
            )
            
            # Update status
            resource["status"] = status
            
            # Patch status
            self.api.patch_namespaced_custom_object_status(
                group=self.group,
                version=self.version,
                namespace=namespace,
                plural=self.plural,
                name=name,
                body=resource
            )
            
            logger.info(f"Updated status for {name}: {status.get('phase', 'Unknown')}")
            
        except ApiException as e:
            logger.error(f"Failed to update status for {name}: {e}")
    
    def create_job_pod(
        self,
        job_name: str,
        spec: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> str:
        """
        Create a Kubernetes pod for fine-tuning job.
        
        Args:
            job_name: Job name
            spec: FineTuningJob spec
            namespace: Optional namespace
            
        Returns:
            Pod name
        """
        namespace = namespace or self.namespace
        
        # Build container command
        cmd = [
            "python3", "-m", "finetuning.base.app",
            "--model-id", spec["baseModel"]["modelId"],
            "--dataset-path", spec["dataset"]["source"],
            "--output-dir", "/workspace/output",
            "--method", spec["method"]
        ]
        
        # Add hyperparameters
        if "hyperparameters" in spec:
            hp = spec["hyperparameters"]
            if "learningRate" in hp:
                cmd.extend(["--learning-rate", str(hp["learningRate"])])
            if "batchSize" in hp:
                cmd.extend(["--batch-size", str(hp["batchSize"])])
            if "epochs" in hp:
                cmd.extend(["--epochs", str(hp["epochs"])])
            if "maxSeqLength" in hp:
                cmd.extend(["--max-seq-length", str(hp["maxSeqLength"])])
        
        # Add LoRA config if method is lora or qlora
        if spec["method"] in ["lora", "qlora"] and "loraConfig" in spec:
            lora = spec["loraConfig"]
            if "r" in lora:
                cmd.extend(["--lora-rank", str(lora["r"])])
            if "loraAlpha" in lora:
                cmd.extend(["--lora-alpha", str(lora["loraAlpha"])])
        
        # Create pod spec
        pod_spec = client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="finetuning",
                    image="aim-finetuning:latest",  # Should be configurable
                    image_pull_policy="IfNotPresent",  # Use local image if available
                    command=cmd,
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="output",
                            mount_path="/workspace/output"
                        ),
                        client.V1VolumeMount(
                            name="templates",
                            mount_path="/workspace/templates",
                            read_only=True
                        )
                    ],
                    resources=spec.get("resources", {}),
                    env=[
                        client.V1EnvVar(name="PYTHONUNBUFFERED", value="1")
                    ]
                )
            ],
            volumes=[
                client.V1Volume(
                    name="output",
                    empty_dir=client.V1EmptyDirVolumeSource()
                ),
                client.V1Volume(
                    name="templates",
                    config_map=client.V1ConfigMapVolumeSource(
                        name="finetuning-templates"
                    )
                )
            ],
            restart_policy="Never"
        )
        
        # Create pod
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=f"{job_name}-pod",
                labels={"job": job_name, "app": "finetuning"}
            ),
            spec=pod_spec
        )
        
        try:
            created_pod = self.core_api.create_namespaced_pod(
                namespace=namespace,
                body=pod
            )
            logger.info(f"Created pod {created_pod.metadata.name} for job {job_name}")
            return created_pod.metadata.name
            
        except ApiException as e:
            logger.error(f"Failed to create pod for {job_name}: {e}")
            raise
    
    def watch_jobs(self) -> None:
        """Watch for FineTuningJob changes and process them."""
        logger.info(f"Starting to watch FineTuningJobs in namespace {self.namespace}")
        
        w = watch.Watch()
        
        try:
            for event in w.stream(
                self.api.list_namespaced_custom_object,
                group=self.group,
                version=self.version,
                namespace=self.namespace,
                plural=self.plural
            ):
                obj = event["object"]
                event_type = event["type"]
                name = obj["metadata"]["name"]
                
                logger.info(f"Event: {event_type} for FineTuningJob {name}")
                
                if event_type == "ADDED":
                    self.handle_job_created(obj)
                elif event_type == "MODIFIED":
                    self.handle_job_modified(obj)
                elif event_type == "DELETED":
                    self.handle_job_deleted(obj)
                    
        except Exception as e:
            logger.error(f"Error watching jobs: {e}")
            raise
    
    def handle_job_created(self, job: Dict[str, Any]) -> None:
        """Handle job creation."""
        name = job["metadata"]["name"]
        spec = job.get("spec", {})
        status = job.get("status", {})
        
        # Skip if already processed
        if status.get("phase") in ["Running", "Succeeded", "Failed"]:
            return
        
        logger.info(f"Handling new FineTuningJob: {name}")
        
        # Update status to Pending
        self.update_status(name, {
            "phase": "Pending",
            "startTime": datetime.utcnow().isoformat() + "Z",
            "message": "Job created, starting pod..."
        })
        
        try:
            # Create pod
            pod_name = self.create_job_pod(name, spec)
            
            # Update status to Running
            self.update_status(name, {
                "phase": "Running",
                "message": f"Pod {pod_name} created, training started"
            })
            
        except Exception as e:
            logger.error(f"Failed to create job {name}: {e}")
            self.update_status(name, {
                "phase": "Failed",
                "message": f"Failed to create pod: {str(e)}"
            })
    
    def handle_job_modified(self, job: Dict[str, Any]) -> None:
        """Handle job modification."""
        name = job["metadata"]["name"]
        status = job.get("status", {})
        
        # Check pod status if job is running
        if status.get("phase") == "Running":
            self.check_pod_status(name)
    
    def handle_job_deleted(self, job: Dict[str, Any]) -> None:
        """Handle job deletion."""
        name = job["metadata"]["name"]
        logger.info(f"FineTuningJob {name} deleted")
        
        # Clean up pod
        try:
            pod_name = f"{name}-pod"
            self.core_api.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace
            )
            logger.info(f"Deleted pod {pod_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore if already deleted
                logger.error(f"Failed to delete pod: {e}")
    
    def check_pod_status(self, job_name: str) -> None:
        """Check pod status and update job status accordingly."""
        pod_name = f"{job_name}-pod"
        
        try:
            pod = self.core_api.read_namespaced_pod(
                name=pod_name,
                namespace=self.namespace
            )
            
            phase = pod.status.phase
            
            if phase == "Succeeded":
                self.update_status(job_name, {
                    "phase": "Succeeded",
                    "completionTime": datetime.utcnow().isoformat() + "Z",
                    "message": "Training completed successfully"
                })
            elif phase == "Failed":
                self.update_status(job_name, {
                    "phase": "Failed",
                    "completionTime": datetime.utcnow().isoformat() + "Z",
                    "message": "Training failed"
                })
                
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {pod_name} not found")
            else:
                logger.error(f"Failed to check pod status: {e}")


def main():
    """Main entry point for controller."""
    namespace = os.getenv("NAMESPACE", "default")
    
    controller = FineTuningJobController(namespace=namespace)
    controller.watch_jobs()


if __name__ == "__main__":
    main()

