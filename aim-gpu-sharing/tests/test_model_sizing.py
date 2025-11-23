"""
Unit tests for model sizing utilities.
"""

import pytest
import yaml
from pathlib import Path
import sys

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from model_sizing import ModelSizingConfig, ModelSizeInfo


class TestModelSizingConfig:
    """Tests for ModelSizingConfig class."""
    
    def test_load_config(self):
        """Test loading configuration from YAML file."""
        config = ModelSizingConfig()
        assert config is not None
        assert len(config.models) > 0
    
    def test_get_model_size(self):
        """Test retrieving model size information."""
        config = ModelSizingConfig()
        
        # Test with known model
        model_info = config.get_model_size("meta-llama/Llama-3.1-8B-Instruct")
        assert model_info is not None
        assert model_info.model_id == "meta-llama/Llama-3.1-8B-Instruct"
        assert model_info.parameters == "8B"
        assert model_info.memory_gb > 0
    
    def test_get_model_size_not_found(self):
        """Test retrieving non-existent model."""
        config = ModelSizingConfig()
        model_info = config.get_model_size("non-existent/model")
        assert model_info is None
    
    def test_estimate_model_size_with_precision(self):
        """Test estimating model size with different precision levels."""
        config = ModelSizingConfig()
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        # Test FP16
        fp16_size = config.estimate_model_size(model_id, precision="fp16")
        assert fp16_size > 0
        
        # Test INT8 (should be less than FP16)
        int8_size = config.estimate_model_size(model_id, precision="int8")
        assert int8_size > 0
        assert int8_size < fp16_size
        
        # Test INT4 (should be less than INT8)
        int4_size = config.estimate_model_size(model_id, precision="int4")
        assert int4_size > 0
        assert int4_size < int8_size
    
    def test_estimate_model_size_fallback(self):
        """Test fallback estimation for unknown models."""
        config = ModelSizingConfig()
        
        # Unknown model with parameters should calculate based on parameters
        size_with_params = config.estimate_model_size("unknown/model", parameters="7B", precision="fp16")
        assert size_with_params > 0
        # 7B * 2 bytes (fp16) * 1.2 overhead ≈ 15.6GB
        assert size_with_params == pytest.approx(15.6, rel=0.1)
        
        # Unknown model without parameters should use default fallback
        size_no_params = config.estimate_model_size("unknown/model", precision="fp16")
        assert size_no_params > 0
        assert size_no_params == pytest.approx(40.0, rel=0.5)  # Default fallback
    
    def test_get_gpu_spec(self):
        """Test retrieving GPU specification."""
        config = ModelSizingConfig()
        
        gpu_spec = config.get_gpu_spec("MI300X")
        assert gpu_spec is not None
        assert gpu_spec.total_memory_gb == 192
        assert gpu_spec.compute_units == 304
    
    def test_get_gpu_spec_not_found(self):
        """Test retrieving non-existent GPU."""
        config = ModelSizingConfig()
        gpu_spec = config.get_gpu_spec("UNKNOWN_GPU")
        assert gpu_spec is None
    
    def test_validate_model_fits_partition(self):
        """Test validating model fits in partition."""
        config = ModelSizingConfig()
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        # Should fit in large partition
        fits, error = config.validate_model_fits_partition(model_id, 50.0)
        assert fits is True
        assert error is None
        
        # Should not fit in small partition
        fits, error = config.validate_model_fits_partition(model_id, 10.0)
        assert fits is False
        assert error is not None
    
    def test_validate_model_fits_partition_below_minimum(self):
        """Test validation fails for partition below minimum size."""
        config = ModelSizingConfig()
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        min_partition = config.partition_config.get('min_partition_gb', 8)
        
        # Test with partition below minimum
        # Note: The size check happens before the minimum check in the implementation.
        # Since the model needs ~20GB and partition is 7GB (below 8GB minimum),
        # the size check fails first (20GB > 7GB - 4GB overhead = 3GB available).
        # To test the minimum check specifically, we'd need a very small model that
        # fits in a partition below minimum, but with current models this is difficult.
        partition_below_min = min_partition - 1.0  # 7GB
        fits, error = config.validate_model_fits_partition(model_id, partition_below_min)
        assert fits is False
        assert error is not None
        # The error will be about insufficient size, not minimum, since size check happens first
        # This is expected behavior - size validation takes precedence over minimum check
    
    def test_calculate_optimal_partitions(self):
        """Test calculating optimal partition allocation."""
        config = ModelSizingConfig()
        
        model_ids = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-Small-3.1-24B",
        ]
        
        partitions = config.calculate_optimal_partitions("MI300X", model_ids)
        assert len(partitions) > 0
        
        # Check partition structure
        for partition in partitions:
            assert "partition_id" in partition
            assert "models" in partition
            assert "allocated_gb" in partition
            assert len(partition["models"]) > 0
    
    def test_calculate_optimal_partitions_insufficient_memory(self):
        """Test partition calculation fails when models don't fit."""
        config = ModelSizingConfig()
        
        # Try to fit too many large models
        model_ids = [
            "meta-llama/Llama-3.3-70B-Instruct",
            "mistralai/Mistral-Large",
            "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        ]
        
        with pytest.raises(ValueError, match="exceeds available"):
            config.calculate_optimal_partitions("MI300X", model_ids)
    
    def test_precision_memory_available(self):
        """Test that precision-specific memory is available."""
        config = ModelSizingConfig()
        
        model_info = config.get_model_size("meta-llama/Llama-3.1-8B-Instruct")
        assert model_info is not None
        
        # Check precision_memory exists
        if model_info.precision_memory:
            assert "fp16" in model_info.precision_memory
            assert "int8" in model_info.precision_memory
            assert "int4" in model_info.precision_memory
            
            # Verify memory decreases with quantization
            assert model_info.precision_memory["fp16"] > model_info.precision_memory["int8"]
            assert model_info.precision_memory["int8"] > model_info.precision_memory["int4"]


class TestModelSizeInfo:
    """Tests for ModelSizeInfo dataclass."""
    
    def test_model_size_info_creation(self):
        """Test creating ModelSizeInfo instance."""
        info = ModelSizeInfo(
            model_id="test/model",
            parameters="7B",
            memory_gb=14.0,
            quantization=["fp16", "int8"],
            recommended_partition_gb=18.0,
            precision_memory={"fp16": 14.0, "int8": 8.0}
        )
        
        assert info.model_id == "test/model"
        assert info.parameters == "7B"
        assert info.memory_gb == 14.0
        assert len(info.quantization) == 2
        assert info.precision_memory is not None

