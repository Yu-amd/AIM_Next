"""
Prometheus Metrics Exporter for GPU Sharing

Exposes metrics about partitions, models, and scheduler operations.
"""

import os
import sys
import time
import logging
from typing import Dict, Optional
from flask import Flask
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge, Counter, Histogram

# Add runtime to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../runtime'))

from rocm_partitioner_real import ROCmPartitionerReal
from model_scheduler import ModelScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
partition_memory_bytes = Gauge(
    'aim_gpu_partition_memory_bytes',
    'Memory usage per partition in bytes',
    ['partition_id', 'compute_mode', 'memory_mode']
)

partition_memory_allocated_bytes = Gauge(
    'aim_gpu_partition_memory_allocated_bytes',
    'Allocated memory per partition in bytes',
    ['partition_id']
)

partition_memory_available_bytes = Gauge(
    'aim_gpu_partition_memory_available_bytes',
    'Available memory per partition in bytes',
    ['partition_id']
)

partition_utilization = Gauge(
    'aim_gpu_partition_utilization',
    'Partition utilization (0-1)',
    ['partition_id']
)

model_memory_bytes = Gauge(
    'aim_model_memory_bytes',
    'Memory allocated per model in bytes',
    ['model_id', 'partition_id']
)

model_request_latency_seconds = Histogram(
    'aim_model_request_latency_seconds',
    'Request latency per model in seconds',
    ['model_id', 'partition_id'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

model_requests_total = Counter(
    'aim_model_requests_total',
    'Total requests per model',
    ['model_id', 'partition_id', 'status']
)

scheduler_operations_total = Counter(
    'aim_scheduler_operations_total',
    'Scheduler operation counts',
    ['operation', 'status']
)

scheduler_queue_depth = Gauge(
    'aim_scheduler_queue_depth',
    'Number of models waiting in scheduler queue',
    ['priority']
)

gpu_total_memory_bytes = Gauge(
    'aim_gpu_total_memory_bytes',
    'Total GPU memory in bytes',
    ['gpu_id']
)

gpu_partition_count = Gauge(
    'aim_gpu_partition_count',
    'Number of partitions',
    ['gpu_id', 'compute_mode', 'memory_mode']
)


class MetricsExporter:
    """Metrics exporter for GPU sharing system."""
    
    def __init__(self, gpu_id: int = 0):
        """
        Initialize metrics exporter.
        
        Args:
            gpu_id: GPU device ID
        """
        self.gpu_id = gpu_id
        
        # Initialize partitioner and scheduler
        self.partitioner = ROCmPartitionerReal(gpu_id=gpu_id)
        if not self.partitioner.amd_smi_available:
            logger.warning("amd-smi not available - metrics will be limited")
            self.partitioner = None
        else:
            # Initialize partitioner
            compute, memory = self.partitioner.get_current_partition_mode()
            from rocm_partitioner_real import ComputePartitionMode, MemoryPartitionMode
            compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
            memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
            
            if not self.partitioner.initialize("MI300X", compute_mode, memory_mode):
                logger.warning("Failed to initialize partitioner")
                self.partitioner = None
        
        if self.partitioner:
            self.scheduler = ModelScheduler(partitioner=self.partitioner, gpu_id=gpu_id)
        else:
            self.scheduler = None
        
        logger.info(f"Metrics exporter initialized for GPU {gpu_id}")
    
    def collect_partition_metrics(self):
        """Collect metrics from partitions."""
        if not self.partitioner or not self.partitioner._initialized:
            return
        
        # Get partition modes
        compute_mode = self.partitioner.compute_mode.value if self.partitioner.compute_mode else 'SPX'
        memory_mode = self.partitioner.memory_mode.value if self.partitioner.memory_mode else 'NPS1'
        
        # GPU-level metrics
        gpu_spec = self.partitioner.sizing_config.get_gpu_spec("MI300X")
        if gpu_spec:
            gpu_total_memory_bytes.labels(gpu_id=self.gpu_id).set(
                gpu_spec.total_memory_gb * (1024 ** 3)
            )
        
        gpu_partition_count.labels(
            gpu_id=self.gpu_id,
            compute_mode=compute_mode,
            memory_mode=memory_mode
        ).set(len(self.partitioner.partitions))
        
        # Partition-level metrics
        for partition_id, partition in self.partitioner.partitions.items():
            partition_memory_bytes.labels(
                partition_id=partition_id,
                compute_mode=compute_mode,
                memory_mode=memory_mode
            ).set(partition.size_bytes)
            
            partition_memory_allocated_bytes.labels(
                partition_id=partition_id
            ).set(partition.allocated_bytes)
            
            partition_memory_available_bytes.labels(
                partition_id=partition_id
            ).set(partition.size_bytes - partition.allocated_bytes)
            
            # Utilization (allocated / total)
            if partition.size_bytes > 0:
                utilization = partition.allocated_bytes / partition.size_bytes
                partition_utilization.labels(partition_id=partition_id).set(utilization)
    
    def collect_model_metrics(self):
        """Collect metrics from scheduled models."""
        if not self.scheduler:
            return
        
        # Get scheduled models
        scheduled_models = self.scheduler.get_scheduled_models()
        
        for model_id, model_info in scheduled_models.items():
            partition_id = model_info.partition_id
            memory_bytes = model_info.memory_gb * (1024 ** 3)
            
            model_memory_bytes.labels(
                model_id=model_id,
                partition_id=partition_id
            ).set(memory_bytes)
    
    def collect_scheduler_metrics(self):
        """Collect metrics from scheduler."""
        if not self.scheduler:
            return
        
        # Queue depth by priority (if scheduler tracks this)
        # For now, we'll use scheduled model count as a proxy
        scheduled = self.scheduler.get_scheduled_models()
        total_scheduled = len(scheduled)
        
        # We don't have priority queue tracking yet, so use a single metric
        scheduler_queue_depth.labels(priority='all').set(total_scheduled)
    
    def update_all_metrics(self):
        """Update all metrics."""
        try:
            self.collect_partition_metrics()
            self.collect_model_metrics()
            self.collect_scheduler_metrics()
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")


# Global metrics exporter instance
_metrics_exporter: Optional[MetricsExporter] = None


def get_metrics_exporter() -> MetricsExporter:
    """Get or create metrics exporter instance."""
    global _metrics_exporter
    if _metrics_exporter is None:
        gpu_id = int(os.getenv('GPU_ID', '0'))
        _metrics_exporter = MetricsExporter(gpu_id=gpu_id)
    return _metrics_exporter


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    exporter = get_metrics_exporter()
    exporter.update_all_metrics()
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy'}, 200


def main():
    """Main entry point for metrics exporter."""
    port = int(os.getenv('METRICS_PORT', '8080'))
    host = os.getenv('METRICS_HOST', '0.0.0.0')
    
    logger.info(f"Starting metrics exporter on {host}:{port}")
    app.run(host=host, port=port)


if __name__ == '__main__':
    main()

