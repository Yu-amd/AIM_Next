"""
Prometheus metrics exporter for fine-tuning jobs.

Exposes training metrics, job status, and resource utilization.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not available. Install with: pip install prometheus-client")

logger = logging.getLogger(__name__)


@dataclass
class TrainingMetrics:
    """Training metrics data structure."""
    job_name: str
    model_id: str
    method: str
    current_epoch: int
    total_epochs: int
    current_step: int
    total_steps: int
    train_loss: float
    learning_rate: float
    gpu_utilization: Optional[float] = None
    gpu_memory_used: Optional[float] = None
    gpu_memory_total: Optional[float] = None
    samples_per_second: Optional[float] = None
    tokens_per_second: Optional[float] = None


class FineTuningMetricsExporter:
    """Prometheus metrics exporter for fine-tuning jobs."""
    
    def __init__(self, port: int = 8000):
        """
        Initialize metrics exporter.
        
        Args:
            port: Port to expose Prometheus metrics
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client not installed. Install with: pip install prometheus-client")
        
        self.port = port
        self.server_started = False
        
        # Job status metrics
        self.job_status = Gauge(
            'finetuning_job_status',
            'Fine-tuning job status (0=Pending, 1=Running, 2=Succeeded, 3=Failed, 4=Paused)',
            ['job_name', 'model_id', 'method']
        )
        
        self.job_duration = Histogram(
            'finetuning_job_duration_seconds',
            'Fine-tuning job duration in seconds',
            ['job_name', 'model_id', 'method']
        )
        
        # Training progress metrics
        self.training_epoch = Gauge(
            'finetuning_training_epoch',
            'Current training epoch',
            ['job_name', 'model_id']
        )
        
        self.training_step = Gauge(
            'finetuning_training_step',
            'Current training step',
            ['job_name', 'model_id']
        )
        
        self.training_progress = Gauge(
            'finetuning_training_progress',
            'Training progress percentage (0-100)',
            ['job_name', 'model_id']
        )
        
        # Training performance metrics
        self.train_loss = Gauge(
            'finetuning_train_loss',
            'Current training loss',
            ['job_name', 'model_id', 'epoch']
        )
        
        self.learning_rate = Gauge(
            'finetuning_learning_rate',
            'Current learning rate',
            ['job_name', 'model_id']
        )
        
        self.samples_per_second = Gauge(
            'finetuning_samples_per_second',
            'Training throughput in samples per second',
            ['job_name', 'model_id']
        )
        
        self.tokens_per_second = Gauge(
            'finetuning_tokens_per_second',
            'Training throughput in tokens per second',
            ['job_name', 'model_id']
        )
        
        # Resource utilization metrics
        self.gpu_utilization = Gauge(
            'finetuning_gpu_utilization_percent',
            'GPU utilization percentage',
            ['job_name', 'gpu_id']
        )
        
        self.gpu_memory_used = Gauge(
            'finetuning_gpu_memory_used_bytes',
            'GPU memory used in bytes',
            ['job_name', 'gpu_id']
        )
        
        self.gpu_memory_total = Gauge(
            'finetuning_gpu_memory_total_bytes',
            'Total GPU memory in bytes',
            ['job_name', 'gpu_id']
        )
        
        # Checkpoint metrics
        self.checkpoint_count = Counter(
            'finetuning_checkpoints_total',
            'Total number of checkpoints saved',
            ['job_name', 'model_id']
        )
        
        self.checkpoint_size = Histogram(
            'finetuning_checkpoint_size_bytes',
            'Checkpoint size in bytes',
            ['job_name', 'model_id']
        )
        
        logger.info(f"Metrics exporter initialized (port: {port})")
    
    def start_server(self) -> None:
        """Start Prometheus metrics HTTP server."""
        if not self.server_started:
            start_http_server(self.port)
            self.server_started = True
            logger.info(f"Prometheus metrics server started on port {self.port}")
            logger.info(f"Metrics available at http://localhost:{self.port}/metrics")
    
    def update_job_status(
        self,
        job_name: str,
        model_id: str,
        method: str,
        status: str
    ) -> None:
        """
        Update job status metric.
        
        Args:
            job_name: Job name
            model_id: Model identifier
            method: Fine-tuning method
            status: Job status (Pending, Running, Succeeded, Failed, Paused)
        """
        status_map = {
            "Pending": 0,
            "Running": 1,
            "Succeeded": 2,
            "Failed": 3,
            "Paused": 4
        }
        
        status_value = status_map.get(status, 0)
        self.job_status.labels(
            job_name=job_name,
            model_id=model_id,
            method=method
        ).set(status_value)
        
        logger.debug(f"Updated job status: {job_name} -> {status}")
    
    def update_training_metrics(self, metrics: TrainingMetrics) -> None:
        """
        Update training metrics.
        
        Args:
            metrics: TrainingMetrics object
        """
        # Progress metrics
        self.training_epoch.labels(
            job_name=metrics.job_name,
            model_id=metrics.model_id
        ).set(metrics.current_epoch)
        
        self.training_step.labels(
            job_name=metrics.job_name,
            model_id=metrics.model_id
        ).set(metrics.current_step)
        
        # Calculate progress percentage
        if metrics.total_steps > 0:
            progress = (metrics.current_step / metrics.total_steps) * 100
        elif metrics.total_epochs > 0:
            progress = (metrics.current_epoch / metrics.total_epochs) * 100
        else:
            progress = 0
        
        self.training_progress.labels(
            job_name=metrics.job_name,
            model_id=metrics.model_id
        ).set(progress)
        
        # Performance metrics
        self.train_loss.labels(
            job_name=metrics.job_name,
            model_id=metrics.model_id,
            epoch=str(metrics.current_epoch)
        ).set(metrics.train_loss)
        
        self.learning_rate.labels(
            job_name=metrics.job_name,
            model_id=metrics.model_id
        ).set(metrics.learning_rate)
        
        if metrics.samples_per_second:
            self.samples_per_second.labels(
                job_name=metrics.job_name,
                model_id=metrics.model_id
            ).set(metrics.samples_per_second)
        
        if metrics.tokens_per_second:
            self.tokens_per_second.labels(
                job_name=metrics.job_name,
                model_id=metrics.model_id
            ).set(metrics.tokens_per_second)
        
        # GPU metrics
        if metrics.gpu_utilization is not None:
            self.gpu_utilization.labels(
                job_name=metrics.job_name,
                gpu_id="0"
            ).set(metrics.gpu_utilization)
        
        if metrics.gpu_memory_used is not None:
            self.gpu_memory_used.labels(
                job_name=metrics.job_name,
                gpu_id="0"
            ).set(metrics.gpu_memory_used)
        
        if metrics.gpu_memory_total is not None:
            self.gpu_memory_total.labels(
                job_name=metrics.job_name,
                gpu_id="0"
            ).set(metrics.gpu_memory_total)
        
        logger.debug(f"Updated training metrics for {metrics.job_name}")
    
    def record_checkpoint(
        self,
        job_name: str,
        model_id: str,
        checkpoint_size: int
    ) -> None:
        """
        Record checkpoint creation.
        
        Args:
            job_name: Job name
            model_id: Model identifier
            checkpoint_size: Checkpoint size in bytes
        """
        self.checkpoint_count.labels(
            job_name=job_name,
            model_id=model_id
        ).inc()
        
        self.checkpoint_size.labels(
            job_name=job_name,
            model_id=model_id
        ).observe(checkpoint_size)
        
        logger.debug(f"Recorded checkpoint for {job_name}: {checkpoint_size} bytes")
    
    def record_job_duration(
        self,
        job_name: str,
        model_id: str,
        method: str,
        duration_seconds: float
    ) -> None:
        """
        Record job duration.
        
        Args:
            job_name: Job name
            model_id: Model identifier
            method: Fine-tuning method
            duration_seconds: Job duration in seconds
        """
        self.job_duration.labels(
            job_name=job_name,
            model_id=model_id,
            method=method
        ).observe(duration_seconds)
        
        logger.debug(f"Recorded job duration for {job_name}: {duration_seconds}s")


def get_gpu_metrics() -> Dict[str, Any]:
    """
    Get GPU utilization and memory metrics.
    
    Returns:
        Dictionary with GPU metrics
    """
    metrics = {
        "gpu_utilization": None,
        "gpu_memory_used": None,
        "gpu_memory_total": None
    }
    
    try:
        # Try AMD GPU (amd-smi)
        import subprocess
        result = subprocess.run(
            ["amd-smi", "--showmeminfo", "vram", "-g", "0"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse amd-smi output
            for line in result.stdout.split('\n'):
                if 'VRAM Total' in line:
                    # Extract total memory
                    parts = line.split()
                    if len(parts) >= 3:
                        metrics["gpu_memory_total"] = float(parts[-2]) * 1024 * 1024 * 1024  # Convert to bytes
                elif 'VRAM Used' in line:
                    # Extract used memory
                    parts = line.split()
                    if len(parts) >= 3:
                        metrics["gpu_memory_used"] = float(parts[-2]) * 1024 * 1024 * 1024  # Convert to bytes
            
            # Calculate utilization (simplified)
            if metrics["gpu_memory_total"] and metrics["gpu_memory_used"]:
                metrics["gpu_utilization"] = (metrics["gpu_memory_used"] / metrics["gpu_memory_total"]) * 100
    except Exception as e:
        logger.debug(f"Could not get GPU metrics: {e}")
    
    return metrics

