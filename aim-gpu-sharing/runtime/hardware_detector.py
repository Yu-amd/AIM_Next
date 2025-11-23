"""
Hardware Detection for ROCm Partitioning

This module detects available hardware and automatically selects the
appropriate partitioner implementation (simulation vs real hardware).
"""

import os
import subprocess
import logging
from typing import Optional, Tuple, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class HardwareCapability(Enum):
    """Hardware capability levels."""
    NONE = "none"  # No GPU hardware
    SIMULATION = "simulation"  # Can simulate but no real partitioning
    REAL_PARTITIONING = "real"  # Can use actual ROCm partition modes


class GPUHWInfo:
    """GPU hardware information."""
    def __init__(
        self,
        gpu_id: int,
        model_name: Optional[str] = None,
        supports_partitioning: bool = False,
        amd_smi_available: bool = False,
        rocm_available: bool = False
    ):
        self.gpu_id = gpu_id
        self.model_name = model_name
        self.supports_partitioning = supports_partitioning
        self.amd_smi_available = amd_smi_available
        self.rocm_available = rocm_available
    
    def __repr__(self):
        return (
            f"GPUHWInfo(gpu_id={self.gpu_id}, model={self.model_name}, "
            f"partitioning={self.supports_partitioning})"
        )


class HardwareDetector:
    """
    Detects GPU hardware and ROCm capabilities.
    
    Automatically determines if real partitioning is available or
    if simulation mode should be used.
    """
    
    def __init__(self):
        """Initialize hardware detector."""
        self._cache: Dict[int, GPUHWInfo] = {}
        self._amd_smi_available: Optional[bool] = None
        self._rocm_available: Optional[bool] = None
    
    def detect_amd_smi(self) -> bool:
        """
        Detect if amd-smi is available.
        
        Returns:
            True if amd-smi is available, False otherwise
        """
        if self._amd_smi_available is not None:
            return self._amd_smi_available
        
        try:
            result = subprocess.run(
                ["amd-smi", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._amd_smi_available = (result.returncode == 0)
            return self._amd_smi_available
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            self._amd_smi_available = False
            return False
    
    def detect_rocm(self) -> bool:
        """
        Detect if ROCm is installed.
        
        Returns:
            True if ROCm is available, False otherwise
        """
        if self._rocm_available is not None:
            return self._rocm_available
        
        # Check ROCm path
        rocm_path = os.environ.get('ROCM_PATH', '/opt/rocm')
        self._rocm_available = os.path.exists(rocm_path)
        return self._rocm_available
    
    def detect_gpu_model(self, gpu_id: int) -> Optional[str]:
        """
        Detect GPU model name using amd-smi.
        
        Args:
            gpu_id: GPU device ID
        
        Returns:
            GPU model name or None if unavailable
        """
        if not self.detect_amd_smi():
            return None
        
        try:
            result = subprocess.run(
                ["amd-smi", "-i", str(gpu_id), "--showproductname"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse output to extract model name
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Product Name' in line or 'GPU' in line:
                        # Extract model name (e.g., "AMD Instinct MI300X")
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if 'MI' in part.upper():
                                # Found MI series
                                model = parts[i]
                                if i + 1 < len(parts) and parts[i+1].isdigit():
                                    model += parts[i+1]
                                return model
                return None
            return None
        except Exception as e:
            logger.debug(f"Failed to detect GPU model: {e}")
            return None
    
    def supports_partitioning(self, gpu_id: int) -> bool:
        """
        Check if GPU supports partitioning modes.
        
        Currently supports MI300 series (MI300X, MI325X, MI350X, etc.)
        
        Args:
            gpu_id: GPU device ID
        
        Returns:
            True if GPU supports partitioning, False otherwise
        """
        model_name = self.detect_gpu_model(gpu_id)
        if not model_name:
            return False
        
        # Check if it's MI300 series
        model_upper = model_name.upper()
        mi300_models = ['MI300', 'MI325', 'MI350', 'MI355']
        return any(model in model_upper for model in mi300_models)
    
    def detect_gpu(self, gpu_id: int) -> GPUHWInfo:
        """
        Detect GPU hardware information.
        
        Args:
            gpu_id: GPU device ID
        
        Returns:
            GPUHWInfo object with hardware details
        """
        if gpu_id in self._cache:
            return self._cache[gpu_id]
        
        amd_smi_available = self.detect_amd_smi()
        rocm_available = self.detect_rocm()
        
        model_name = None
        supports_partitioning = False
        
        if amd_smi_available:
            model_name = self.detect_gpu_model(gpu_id)
            if model_name:
                supports_partitioning = self.supports_partitioning(gpu_id)
        
        info = GPUHWInfo(
            gpu_id=gpu_id,
            model_name=model_name,
            supports_partitioning=supports_partitioning,
            amd_smi_available=amd_smi_available,
            rocm_available=rocm_available
        )
        
        self._cache[gpu_id] = info
        return info
    
    def get_capability(self, gpu_id: int) -> HardwareCapability:
        """
        Get hardware capability level for a GPU.
        
        Args:
            gpu_id: GPU device ID
        
        Returns:
            HardwareCapability enum value
        """
        info = self.detect_gpu(gpu_id)
        
        if info.supports_partitioning and info.amd_smi_available:
            return HardwareCapability.REAL_PARTITIONING
        elif info.rocm_available or info.amd_smi_available:
            return HardwareCapability.SIMULATION
        else:
            return HardwareCapability.NONE
    
    def list_available_gpus(self) -> list[int]:
        """
        List available GPU device IDs.
        
        Returns:
            List of GPU device IDs
        """
        if not self.detect_amd_smi():
            return []
        
        try:
            result = subprocess.run(
                ["amd-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                gpu_ids = []
                for line in result.stdout.split('\n'):
                    # Parse "GPU 0: ..." format
                    if 'GPU' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'GPU' and i + 1 < len(parts):
                                try:
                                    gpu_id = int(parts[i + 1].rstrip(':'))
                                    gpu_ids.append(gpu_id)
                                except ValueError:
                                    pass
                return sorted(gpu_ids)
            return []
        except Exception as e:
            logger.debug(f"Failed to list GPUs: {e}")
            return []


def get_partitioner_class(gpu_id: int = 0):
    """
    Automatically select the appropriate partitioner class.
    
    Args:
        gpu_id: GPU device ID
    
    Returns:
        Tuple of (partitioner_class, capability, info)
    """
    detector = HardwareDetector()
    capability = detector.get_capability(gpu_id)
    info = detector.detect_gpu(gpu_id)
    
    if capability == HardwareCapability.REAL_PARTITIONING:
        try:
            from rocm_partitioner_real import ROCmPartitionerReal
            logger.info(
                f"Using real hardware partitioner for GPU {gpu_id} "
                f"({info.model_name})"
            )
            return ROCmPartitionerReal, capability, info
        except ImportError:
            logger.warning(
                "Real partitioner not available, falling back to simulation"
            )
            from rocm_partitioner import ROCmPartitioner
            return ROCmPartitioner, HardwareCapability.SIMULATION, info
    else:
        from rocm_partitioner import ROCmPartitioner
        if capability == HardwareCapability.SIMULATION:
            logger.info(f"Using simulation partitioner for GPU {gpu_id}")
        else:
            logger.warning(
                f"No GPU hardware detected for GPU {gpu_id}, "
                "using simulation mode"
            )
        return ROCmPartitioner, capability, info

