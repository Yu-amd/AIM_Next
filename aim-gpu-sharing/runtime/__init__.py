"""
AIM GPU Sharing Runtime Components

This package provides runtime components for GPU memory partitioning
and multi-model deployment on AMD GPUs using ROCm.
"""

from .model_sizing import ModelSizingConfig, ModelSizeInfo
from .rocm_partitioner import ROCmPartitioner, MemoryPartition
from .model_scheduler import ModelScheduler, ModelInstance, ModelStatus
from .resource_isolator import ResourceIsolator, ComputeLimits
from .hardware_detector import (
    HardwareDetector,
    HardwareCapability,
    GPUHWInfo,
    get_partitioner_class
)
from .auto_partitioner import create_partitioner, initialize_partitioner

# Try to import real partitioner (may not be available)
try:
    from .rocm_partitioner_real import (
        ROCmPartitionerReal,
        ComputePartitionMode,
        MemoryPartitionMode
    )
    __all__ = [
        'ModelSizingConfig',
        'ModelSizeInfo',
        'ROCmPartitioner',
        'ROCmPartitionerReal',
        'MemoryPartition',
        'ModelScheduler',
        'ModelInstance',
        'ModelStatus',
        'ResourceIsolator',
        'ComputeLimits',
        'HardwareDetector',
        'HardwareCapability',
        'GPUHWInfo',
        'get_partitioner_class',
        'create_partitioner',
        'initialize_partitioner',
        'ComputePartitionMode',
        'MemoryPartitionMode',
    ]
except ImportError:
    __all__ = [
        'ModelSizingConfig',
        'ModelSizeInfo',
        'ROCmPartitioner',
        'MemoryPartition',
        'ModelScheduler',
        'ModelInstance',
        'ModelStatus',
        'ResourceIsolator',
        'ComputeLimits',
        'HardwareDetector',
        'HardwareCapability',
        'GPUHWInfo',
        'get_partitioner_class',
        'create_partitioner',
        'initialize_partitioner',
    ]

