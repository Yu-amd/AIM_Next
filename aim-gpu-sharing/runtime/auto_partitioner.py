"""
Auto Partitioner - Automatically selects simulation or real partitioner.

This module provides a unified interface that automatically detects
hardware and selects the appropriate partitioner implementation.
"""

import logging
from typing import Optional, Union

from hardware_detector import (
    get_partitioner_class,
    HardwareDetector,
    HardwareCapability
)

logger = logging.getLogger(__name__)


def create_partitioner(
    gpu_id: int = 0,
    config_path: Optional[str] = None,
    force_simulation: bool = False
) -> Union['ROCmPartitioner', 'ROCmPartitionerReal']:
    """
    Create partitioner with automatic hardware detection.
    
    Args:
        gpu_id: GPU device ID
        config_path: Path to model sizing configuration
        force_simulation: Force simulation mode even if hardware is available
    
    Returns:
        ROCmPartitioner or ROCmPartitionerReal instance
    """
    if force_simulation:
        from rocm_partitioner import ROCmPartitioner
        logger.info(f"Using simulation partitioner (forced) for GPU {gpu_id}")
        return ROCmPartitioner(gpu_id=gpu_id, config_path=config_path)
    
    partitioner_class, capability, info = get_partitioner_class(gpu_id)
    
    partitioner = partitioner_class(gpu_id=gpu_id, config_path=config_path)
    
    # Log hardware info
    if info.model_name:
        logger.info(
            f"Detected GPU {gpu_id}: {info.model_name} "
            f"(capability: {capability.value})"
        )
    else:
        logger.info(
            f"GPU {gpu_id}: {capability.value} mode"
        )
    
    return partitioner


def initialize_partitioner(
    partitioner: Union['ROCmPartitioner', 'ROCmPartitionerReal'],
    gpu_name: str = "MI300X",
    **kwargs
) -> bool:
    """
    Initialize partitioner with appropriate settings based on type.
    
    Args:
        partitioner: Partitioner instance
        gpu_name: GPU model name
        **kwargs: Additional initialization parameters
    
    Returns:
        True if initialization successful, False otherwise
    """
    # Check if it's real partitioner
    if hasattr(partitioner, 'set_compute_partition_mode'):
        # Real partitioner - use partition modes
        from rocm_partitioner_real import (
            ComputePartitionMode,
            MemoryPartitionMode
        )
        
        compute_mode = kwargs.get(
            'compute_mode',
            ComputePartitionMode.CPX
        )
        memory_mode = kwargs.get(
            'memory_mode',
            MemoryPartitionMode.NPS4
        )
        
        return partitioner.initialize(
            gpu_name=gpu_name,
            compute_mode=compute_mode,
            memory_mode=memory_mode
        )
    else:
        # Simulation partitioner - use partition sizes
        partition_sizes = kwargs.get(
            'partition_sizes_gb',
            [40.0, 40.0, 40.0, 40.0]  # Default: 4 partitions of 40GB
        )
        
        return partitioner.initialize(gpu_name, partition_sizes)

