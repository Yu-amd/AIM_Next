"""
ROCm Memory Partitioner - Real Implementation

This module provides ROCm-based GPU memory partitioning using actual
AMD Instinct MI300 compute and memory partition modes.

Based on: https://rocm.blogs.amd.com/software-tools-optimization/compute-memory-modes/

Supports:
- Compute partitioning: SPX, CPX, TPX
- Memory partitioning: NPS1, NPS4
- SR-IOV Virtual Functions for isolation
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Handle both relative and absolute imports
try:
    from .model_sizing import ModelSizingConfig, ModelSizeInfo
except ImportError:
    from model_sizing import ModelSizingConfig, ModelSizeInfo

logger = logging.getLogger(__name__)


class ComputePartitionMode(Enum):
    """Compute partitioning modes for MI300."""
    SPX = "SPX"  # Single Partition - all XCDs as one device
    CPX = "CPX"  # Core Partitioned - each XCD as separate device
    TPX = "TPX"  # (Future support)


class MemoryPartitionMode(Enum):
    """Memory partitioning modes (NUMA Per Socket)."""
    NPS1 = "NPS1"  # All memory accessible to all XCDs
    NPS4 = "NPS4"  # Memory quadrants (requires CPX mode)


@dataclass
class MemoryPartition:
    """Represents a GPU memory partition."""
    partition_id: int
    vf_id: Optional[int] = None  # Virtual Function ID (SR-IOV)
    xcd_id: Optional[int] = None  # XCD ID in CPX mode
    size_bytes: int = 0
    allocated_bytes: int = 0
    models: List[str] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.models is None:
            self.models = []


class ROCmPartitionerReal:
    """
    Real ROCm-based GPU memory partitioner using MI300 partition modes.
    
    This implementation uses actual amd-smi commands and ROCm APIs to
    configure compute and memory partitions on MI300 series GPUs.
    """
    
    def __init__(
        self,
        gpu_id: int = 0,
        config_path: Optional[str] = None
    ):
        """
        Initialize ROCm partitioner with real hardware support.
        
        Args:
            gpu_id: Physical GPU device ID
            config_path: Path to model sizing configuration
        """
        self.gpu_id = gpu_id
        self.sizing_config = ModelSizingConfig(config_path)
        self.partitions: Dict[int, MemoryPartition] = {}
        self._initialized = False
        
        # Partition mode configuration
        self.compute_mode: Optional[ComputePartitionMode] = None
        self.memory_mode: Optional[MemoryPartitionMode] = None
        
        # Check for amd-smi and ROCm
        self._check_rocm_availability()
    
    def _check_rocm_availability(self):
        """Check if ROCm and amd-smi are available."""
        # Check for amd-smi
        try:
            result = subprocess.run(
                ["amd-smi", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.amd_smi_available = True
                logger.info("amd-smi is available")
            else:
                self.amd_smi_available = False
                logger.warning("amd-smi not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.amd_smi_available = False
            logger.warning("amd-smi command not found")
        
        # Check for ROCm path
        rocm_path = os.environ.get('ROCM_PATH', '/opt/rocm')
        self.rocm_available = os.path.exists(rocm_path)
        
        if not self.rocm_available:
            logger.warning(f"ROCm not found at {rocm_path}")
    
    def get_current_partition_mode(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get current compute and memory partition modes.
        
        Returns:
            Tuple of (compute_mode, memory_mode) or (None, None) if unavailable
        """
        if not self.amd_smi_available:
            return None, None
        
        try:
            # Query compute partition mode
            result = subprocess.run(
                ["amd-smi", "query", "--compute-partition"],
                capture_output=True,
                text=True,
                timeout=5
            )
            compute_mode = result.stdout.strip() if result.returncode == 0 else None
            
            # Query memory partition mode
            result = subprocess.run(
                ["amd-smi", "query", "--memory-partition"],
                capture_output=True,
                text=True,
                timeout=5
            )
            memory_mode = result.stdout.strip() if result.returncode == 0 else None
            
            return compute_mode, memory_mode
        except Exception as e:
            logger.error(f"Failed to query partition modes: {e}")
            return None, None
    
    def set_compute_partition_mode(
        self,
        mode: ComputePartitionMode
    ) -> bool:
        """
        Set compute partition mode using amd-smi.
        
        Args:
            mode: Compute partition mode (SPX, CPX, TPX)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.amd_smi_available:
            logger.error("amd-smi not available")
            return False
        
        try:
            result = subprocess.run(
                ["amd-smi", "set", "--compute-partition", mode.value],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            self.compute_mode = mode
            logger.info(f"Set compute partition mode to {mode.value}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set compute partition mode: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error setting compute partition mode: {e}")
            return False
    
    def set_memory_partition_mode(
        self,
        mode: MemoryPartitionMode
    ) -> bool:
        """
        Set memory partition mode using amd-smi.
        
        Args:
            mode: Memory partition mode (NPS1, NPS4)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.amd_smi_available:
            logger.error("amd-smi not available")
            return False
        
        # Validate compatibility
        if mode == MemoryPartitionMode.NPS4:
            if self.compute_mode != ComputePartitionMode.CPX:
                logger.error("NPS4 requires CPX compute mode")
                return False
        
        try:
            result = subprocess.run(
                ["amd-smi", "set", "--memory-partition", mode.value],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            self.memory_mode = mode
            logger.info(f"Set memory partition mode to {mode.value}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set memory partition mode: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error setting memory partition mode: {e}")
            return False
    
    def initialize(
        self,
        gpu_name: str,
        compute_mode: ComputePartitionMode = ComputePartitionMode.CPX,
        memory_mode: MemoryPartitionMode = MemoryPartitionMode.NPS4,
        partition_sizes_gb: Optional[List[float]] = None
    ) -> bool:
        """
        Initialize partitions using real ROCm partition modes.
        
        For MI300X:
        - CPX mode: Creates 8 logical devices (one per XCD)
        - NPS4 mode: Each device sees 1/4 of memory (local quadrant)
        - NPS1 mode: Each device sees all memory
        
        Args:
            gpu_name: GPU model name (e.g., "MI300X")
            compute_mode: Compute partition mode
            memory_mode: Memory partition mode
            partition_sizes_gb: Optional list of partition sizes (for validation)
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.warning("Partitioner already initialized")
            return False
        
        if not self.amd_smi_available:
            logger.error("amd-smi not available - cannot initialize real partitions")
            return False
        
        # Set compute partition mode
        if not self.set_compute_partition_mode(compute_mode):
            return False
        
        # Set memory partition mode
        if not self.set_memory_partition_mode(memory_mode):
            return False
        
        # Get GPU specification
        gpu_spec = self.sizing_config.get_gpu_spec(gpu_name)
        if not gpu_spec:
            logger.error(f"Unknown GPU: {gpu_name}")
            return False
        
        # Determine number of logical devices based on compute mode
        if compute_mode == ComputePartitionMode.CPX:
            # MI300X has 8 XCDs, each becomes a logical device
            num_partitions = 8
        elif compute_mode == ComputePartitionMode.SPX:
            # Single logical device
            num_partitions = 1
        else:
            logger.error(f"Unsupported compute mode: {compute_mode}")
            return False
        
        # Calculate memory per partition based on memory mode
        if memory_mode == MemoryPartitionMode.NPS4:
            # Each partition gets 1/4 of total memory
            memory_per_partition = gpu_spec.total_memory_gb / 4
        elif memory_mode == MemoryPartitionMode.NPS1:
            # All partitions see full memory (but may be limited by compute)
            memory_per_partition = gpu_spec.total_memory_gb
        else:
            logger.error(f"Unsupported memory mode: {memory_mode}")
            return False
        
        # Create partition objects
        for i in range(num_partitions):
            partition = MemoryPartition(
                partition_id=i,
                xcd_id=i if compute_mode == ComputePartitionMode.CPX else None,
                size_bytes=int(memory_per_partition * (1024 ** 3)),
                allocated_bytes=0,
                models=[],
                is_active=True
            )
            self.partitions[i] = partition
        
        self.gpu_name = gpu_name
        self._initialized = True
        
        logger.info(
            f"Initialized {num_partitions} partitions on {gpu_name} "
            f"({compute_mode.value}/{memory_mode.value})"
        )
        logger.info(
            f"Memory per partition: {memory_per_partition:.1f}GB"
        )
        
        return True
    
    def get_logical_devices(self) -> List[Dict[str, any]]:
        """
        Get list of logical devices after partitioning.
        
        Returns:
            List of device information dictionaries
        """
        if not self._initialized:
            return []
        
        devices = []
        for partition_id, partition in self.partitions.items():
            device_info = {
                "device_id": partition_id,
                "xcd_id": partition.xcd_id,
                "memory_gb": partition.size_bytes / (1024 ** 3),
                "allocated_gb": partition.allocated_bytes / (1024 ** 3),
                "models": partition.models.copy(),
            }
            devices.append(device_info)
        
        return devices
    
    def allocate_model(
        self,
        model_id: str,
        partition_id: int,
        precision: str = "fp16"
    ) -> Tuple[bool, Optional[str]]:
        """
        Allocate a model to a partition.
        
        Args:
            model_id: Model identifier
            partition_id: Target partition ID (logical device ID)
            precision: Model precision (fp16, int8, int4)
        
        Returns:
            Tuple of (success, error_message)
        """
        if not self._initialized:
            return False, "Partitioner not initialized"
        
        if partition_id not in self.partitions:
            return False, f"Partition {partition_id} does not exist"
        
        partition = self.partitions[partition_id]
        
        # Get model memory requirement
        model_size = self.sizing_config.estimate_model_size(
            model_id,
            precision=precision
        )
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
            f"Allocated model {model_id} ({precision}) to partition {partition_id} "
            f"(XCD {partition.xcd_id}, {model_size:.1f}GB)"
        )
        
        return True, None
    
    def get_partition_info(self, partition_id: int) -> Optional[MemoryPartition]:
        """Get information about a partition."""
        return self.partitions.get(partition_id)
    
    def deallocate_model(
        self,
        model_id: str,
        partition_id: int
    ) -> bool:
        """
        Deallocate a model from a partition.
        
        Compatible with simulation partitioner interface.
        
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
    
    def get_environment_variables(self, partition_id: int) -> Dict[str, str]:
        """
        Get environment variables for a partition (logical device).
        
        In CPX mode, each partition is a separate logical device.
        Set ROCR_VISIBLE_DEVICES to the logical device ID.
        
        Args:
            partition_id: Partition ID
        
        Returns:
            Dictionary of environment variables
        """
        if partition_id not in self.partitions:
            return {}
        
        env_vars = {}
        
        # In CPX mode, each partition is a separate logical device
        if self.compute_mode == ComputePartitionMode.CPX:
            # Logical device ID corresponds to partition ID
            env_vars['ROCR_VISIBLE_DEVICES'] = str(partition_id)
        else:
            # SPX mode - single device
            env_vars['ROCR_VISIBLE_DEVICES'] = str(self.gpu_id)
        
        # Add partition metadata
        env_vars['AIM_PARTITION_ID'] = str(partition_id)
        env_vars['AIM_COMPUTE_MODE'] = self.compute_mode.value if self.compute_mode else "UNKNOWN"
        env_vars['AIM_MEMORY_MODE'] = self.memory_mode.value if self.memory_mode else "UNKNOWN"
        
        partition = self.partitions[partition_id]
        if partition.xcd_id is not None:
            env_vars['AIM_XCD_ID'] = str(partition.xcd_id)
        
        return env_vars
    
    def reset_partitions(self) -> bool:
        """
        Reset partition modes to default (SPX/NPS1).
        
        Returns:
            True if successful, False otherwise
        """
        if not self.amd_smi_available:
            return False
        
        try:
            # Reset compute partition
            subprocess.run(
                ["amd-smi", "reset", "--compute-partition"],
                capture_output=True,
                timeout=30,
                check=True
            )
            
            # Reset memory partition
            subprocess.run(
                ["amd-smi", "reset", "--memory-partition"],
                capture_output=True,
                timeout=30,
                check=True
            )
            
            self._initialized = False
            self.partitions.clear()
            logger.info("Reset partition modes to default")
            return True
        except Exception as e:
            logger.error(f"Failed to reset partitions: {e}")
            return False
    
    def deallocate_model(
        self,
        model_id: str,
        partition_id: int
    ) -> bool:
        """
        Deallocate a model from a partition.
        
        Compatible with simulation partitioner interface.
        
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


    
    def get_available_partitions(self) -> List[int]:
        """
        Get list of partition IDs with available space.
        
        Compatible with simulation partitioner interface.
        
        Returns:
            List of partition IDs with available space
        """
        available = []
        min_size = (
            self.sizing_config.partition_config.get('min_partition_gb', 8)
            * (1024 ** 3)
        )
        
        for partition_id, partition in self.partitions.items():
            if partition.is_active:
                available_bytes = partition.size_bytes - partition.allocated_bytes
                if available_bytes >= min_size:
                    available.append(partition_id)
        return available
    
    def get_partition_utilization(self) -> Dict[int, float]:
        """
        Get memory utilization for each partition.
        
        Compatible with simulation partitioner interface.
        
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
        
        Compatible with simulation partitioner interface.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self._initialized:
            errors.append("Partitioner not initialized")
            return False, errors
        
        # Check for memory overflows
        for partition_id, partition in self.partitions.items():
            if partition.allocated_bytes > partition.size_bytes:
                errors.append(
                    f"Partition {partition_id} overflow: "
                    f"{partition.allocated_bytes / (1024**3):.1f}GB allocated "
                    f"in {partition.size_bytes / (1024**3):.1f}GB partition"
                )
        
        return len(errors) == 0, errors
