"""
ROCm Memory Partitioner - Simulation/Development Mode

⚠️ NOTE: This is a simulation implementation for development/testing.
For production use with real hardware, use rocm_partitioner_real.py which
uses actual amd-smi commands and ROCm partition modes.

See ROCM_PARTITIONING.md for details on real hardware implementation.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Handle both relative and absolute imports
try:
    from .model_sizing import ModelSizingConfig, ModelSizeInfo
except ImportError:
    from model_sizing import ModelSizingConfig, ModelSizeInfo

logger = logging.getLogger(__name__)


@dataclass
class MemoryPartition:
    """Represents a GPU memory partition."""
    partition_id: int
    start_address: int  # Memory address in bytes
    size_bytes: int
    allocated_bytes: int
    models: List[str]
    is_active: bool = True


class ROCmPartitioner:
    """
    ROCm-based GPU memory partitioner.
    
    This class manages memory partitioning on AMD GPUs using ROCm APIs.
    It divides GPU memory into isolated regions for different models.
    """
    
    def __init__(
        self,
        gpu_id: int = 0,
        config_path: Optional[str] = None
    ):
        """
        Initialize ROCm partitioner.
        
        Args:
            gpu_id: GPU device ID
            config_path: Path to model sizing configuration
        """
        self.gpu_id = gpu_id
        self.sizing_config = ModelSizingConfig(config_path)
        self.partitions: Dict[int, MemoryPartition] = {}
        self._initialized = False
        
        # Check if ROCm is available
        self._check_rocm_availability()
    
    def _check_rocm_availability(self):
        """Check if ROCm is available on the system."""
        # Check for ROCm environment variables
        rocm_path = os.environ.get('ROCM_PATH', '/opt/rocm')
        if not os.path.exists(rocm_path):
            logger.warning(
                f"ROCm not found at {rocm_path}. "
                "Partitioning will be simulated."
            )
            self.rocm_available = False
        else:
            self.rocm_available = True
        
        # Check for HIP runtime
        try:
            import hip
            self.hip_available = True
        except ImportError:
            logger.warning(
                "HIP Python bindings not available. "
                "Using simulation mode."
            )
            self.hip_available = False
    
    def initialize(
        self,
        gpu_name: str,
        partition_sizes_gb: List[float]
    ) -> bool:
        """
        Initialize memory partitions on the GPU.
        
        Args:
            gpu_name: GPU model name (e.g., "MI300X")
            partition_sizes_gb: List of partition sizes in GB
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.warning("Partitioner already initialized")
            return False
        
        gpu_spec = self.sizing_config.get_gpu_spec(gpu_name)
        if not gpu_spec:
            logger.error(f"Unknown GPU: {gpu_name}")
            return False
        
        total_memory_bytes = gpu_spec.total_memory_gb * (1024 ** 3)
        total_requested = sum(partition_sizes_gb) * (1024 ** 3)
        
        # Validate total memory
        overhead_bytes = (
            self.sizing_config.partition_config.get('system_overhead_gb', 4)
            * (1024 ** 3)
        )
        available = total_memory_bytes - overhead_bytes
        
        if total_requested > available:
            logger.error(
                f"Total requested partitions {total_requested / (1024**3):.1f}GB "
                f"exceeds available {available / (1024**3):.1f}GB"
            )
            return False
        
        # Create partitions
        current_address = 0
        for i, size_gb in enumerate(partition_sizes_gb):
            size_bytes = int(size_gb * (1024 ** 3))
            
            partition = MemoryPartition(
                partition_id=i,
                start_address=current_address,
                size_bytes=size_bytes,
                allocated_bytes=0,
                models=[],
            )
            
            self.partitions[i] = partition
            current_address += size_bytes
        
        self.gpu_name = gpu_name
        self._initialized = True
        logger.info(
            f"Initialized {len(partition_sizes_gb)} partitions on {gpu_name}"
        )
        
        return True
    
    def allocate_model(
        self,
        model_id: str,
        partition_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Allocate a model to a partition.
        
        Args:
            model_id: Model identifier
            partition_id: Target partition ID
        
        Returns:
            Tuple of (success, error_message)
        """
        if not self._initialized:
            return False, "Partitioner not initialized"
        
        if partition_id not in self.partitions:
            return False, f"Partition {partition_id} does not exist"
        
        partition = self.partitions[partition_id]
        
        # Validate model fits
        model_size = self.sizing_config.estimate_model_size(model_id)
        model_size_bytes = int(model_size * (1024 ** 3))
        
        available = partition.size_bytes - partition.allocated_bytes
        
        if model_size_bytes > available:
            return False, (
                f"Model {model_id} requires {model_size:.1f}GB but partition "
                f"{partition_id} only has {available / (1024**3):.1f}GB available"
            )
        
        # Allocate model
        partition.models.append(model_id)
        partition.allocated_bytes += model_size_bytes
        
        logger.info(
            f"Allocated model {model_id} to partition {partition_id} "
            f"({model_size:.1f}GB)"
        )
        
        return True, None
    
    def deallocate_model(
        self,
        model_id: str,
        partition_id: int
    ) -> bool:
        """
        Deallocate a model from a partition.
        
        Args:
            model_id: Model identifier
            partition_id: Partition ID
        
        Returns:
            True if successful, False otherwise
        """
        if partition_id not in self.partitions:
            return False
        
        partition = self.partitions[partition_id]
        
        if model_id not in partition.models:
            logger.warning(
                f"Model {model_id} not found in partition {partition_id}"
            )
            return False
        
        # Calculate freed memory
        model_size = self.sizing_config.estimate_model_size(model_id)
        model_size_bytes = int(model_size * (1024 ** 3))
        
        partition.models.remove(model_id)
        partition.allocated_bytes -= model_size_bytes
        
        logger.info(
            f"Deallocated model {model_id} from partition {partition_id}"
        )
        
        return True
    
    def get_partition_info(self, partition_id: int) -> Optional[MemoryPartition]:
        """Get information about a partition."""
        return self.partitions.get(partition_id)
    
    def get_available_partitions(self) -> List[int]:
        """Get list of partition IDs with available space."""
        available = []
        for partition_id, partition in self.partitions.items():
            if partition.is_active:
                available_bytes = partition.size_bytes - partition.allocated_bytes
                min_size = (
                    self.sizing_config.partition_config.get('min_partition_gb', 8)
                    * (1024 ** 3)
                )
                if available_bytes >= min_size:
                    available.append(partition_id)
        return available
    
    def get_partition_utilization(self) -> Dict[int, float]:
        """
        Get memory utilization for each partition.
        
        Returns:
            Dictionary mapping partition_id to utilization percentage
        """
        utilization = {}
        for partition_id, partition in self.partitions.items():
            if partition.size_bytes > 0:
                util = (partition.allocated_bytes / partition.size_bytes) * 100
                utilization[partition_id] = util
            else:
                utilization[partition_id] = 0.0
        return utilization
    
    def validate_partitioning(self) -> Tuple[bool, List[str]]:
        """
        Validate current partitioning configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self._initialized:
            errors.append("Partitioner not initialized")
            return False, errors
        
        # Check for memory overflows
        gpu_spec = self.sizing_config.get_gpu_spec(self.gpu_name)
        if gpu_spec:
            total_memory = gpu_spec.total_memory_gb * (1024 ** 3)
            total_allocated = sum(
                p.size_bytes for p in self.partitions.values()
            )
            
            if total_allocated > total_memory:
                errors.append(
                    f"Total partition size {total_allocated / (1024**3):.1f}GB "
                    f"exceeds GPU memory {total_memory / (1024**3):.1f}GB"
                )
        
        # Check individual partitions
        for partition_id, partition in self.partitions.items():
            if partition.allocated_bytes > partition.size_bytes:
                errors.append(
                    f"Partition {partition_id} overflow: "
                    f"{partition.allocated_bytes / (1024**3):.1f}GB allocated "
                    f"in {partition.size_bytes / (1024**3):.1f}GB partition"
                )
        
        return len(errors) == 0, errors

