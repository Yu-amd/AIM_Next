"""
Unit tests for hardware detector.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from hardware_detector import (
    HardwareDetector,
    HardwareCapability,
    GPUHWInfo,
    get_partitioner_class
)


class TestHardwareDetector:
    """Tests for HardwareDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return HardwareDetector()
    
    def test_detect_amd_smi_not_available(self, detector):
        """Test amd-smi detection when not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = detector.detect_amd_smi()
            assert result is False
    
    def test_detect_amd_smi_available(self, detector):
        """Test amd-smi detection when available."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = detector.detect_amd_smi()
            assert result is True
    
    def test_detect_rocm(self, detector, tmp_path):
        """Test ROCm detection."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = detector.detect_rocm()
            assert result is True
    
    def test_detect_gpu_model(self, detector):
        """Test GPU model detection."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Product Name: AMD Instinct MI300X"
            mock_run.return_value = mock_result
            
            model = detector.detect_gpu_model(0)
            assert model is not None
            assert "MI300" in model.upper()
    
    def test_supports_partitioning_mi300(self, detector):
        """Test partitioning support for MI300."""
        with patch.object(detector, 'detect_gpu_model', return_value="MI300X"):
            result = detector.supports_partitioning(0)
            assert result is True
    
    def test_supports_partitioning_other(self, detector):
        """Test partitioning support for non-MI300 GPU."""
        with patch.object(detector, 'detect_gpu_model', return_value="RX7900"):
            result = detector.supports_partitioning(0)
            assert result is False
    
    def test_detect_gpu(self, detector):
        """Test GPU detection."""
        with patch.object(detector, 'detect_amd_smi', return_value=True):
            with patch.object(detector, 'detect_rocm', return_value=True):
                with patch.object(detector, 'detect_gpu_model', return_value="MI300X"):
                    with patch.object(detector, 'supports_partitioning', return_value=True):
                        info = detector.detect_gpu(0)
                        
                        assert info.gpu_id == 0
                        assert info.model_name == "MI300X"
                        assert info.supports_partitioning is True
                        assert info.amd_smi_available is True
    
    def test_get_capability_real(self, detector):
        """Test capability detection for real partitioning."""
        with patch.object(detector, 'detect_gpu') as mock_detect:
            mock_info = GPUHWInfo(
                gpu_id=0,
                model_name="MI300X",
                supports_partitioning=True,
                amd_smi_available=True,
                rocm_available=True
            )
            mock_detect.return_value = mock_info
            
            capability = detector.get_capability(0)
            assert capability == HardwareCapability.REAL_PARTITIONING
    
    def test_get_capability_simulation(self, detector):
        """Test capability detection for simulation."""
        with patch.object(detector, 'detect_gpu') as mock_detect:
            mock_info = GPUHWInfo(
                gpu_id=0,
                model_name=None,
                supports_partitioning=False,
                amd_smi_available=False,
                rocm_available=True
            )
            mock_detect.return_value = mock_info
            
            capability = detector.get_capability(0)
            assert capability == HardwareCapability.SIMULATION
    
    def test_list_available_gpus(self, detector):
        """Test listing available GPUs."""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "GPU 0: AMD Instinct MI300X\nGPU 1: AMD Instinct MI300X"
            mock_run.return_value = mock_result
            
            gpus = detector.list_available_gpus()
            assert len(gpus) == 2
            assert 0 in gpus
            assert 1 in gpus


class TestGetPartitionerClass:
    """Tests for get_partitioner_class function."""
    
    def test_get_partitioner_simulation(self):
        """Test getting simulation partitioner."""
        with patch('hardware_detector.HardwareDetector') as mock_detector_class:
            mock_detector = MagicMock()
            mock_detector.get_capability.return_value = HardwareCapability.SIMULATION
            mock_detector.detect_gpu.return_value = GPUHWInfo(
                gpu_id=0,
                amd_smi_available=False
            )
            mock_detector_class.return_value = mock_detector
            
            partitioner_class, capability, info = get_partitioner_class(0)
            
            assert capability == HardwareCapability.SIMULATION
            # Should return simulation partitioner
            assert 'ROCmPartitioner' in str(partitioner_class)

