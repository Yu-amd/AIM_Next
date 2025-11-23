"""
Unit tests for AIM profile generator.
"""

import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from aim_profile_generator import (
    AIMProfileGenerator,
    AIMProfile,
    PrecisionVariant
)
from model_sizing import ModelSizingConfig


class TestAIMProfileGenerator:
    """Tests for AIMProfileGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a profile generator instance."""
        return AIMProfileGenerator()
    
    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert generator.sizing_config is not None
        assert len(generator.profiles) == 0
    
    def test_generate_profiles_for_model(self, generator):
        """Test generating profiles for a single model."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        variants = [
            PrecisionVariant(precision="fp16", memory_gb=20.0, recommended_partition_gb=25.0),
            PrecisionVariant(precision="int8", memory_gb=13.0, recommended_partition_gb=16.25),
            PrecisionVariant(precision="int4", memory_gb=9.0, recommended_partition_gb=11.25),
        ]
        
        profiles = generator.generate_profiles_for_model(model_id, variants)
        
        assert len(profiles) == 3
        assert all(isinstance(p, AIMProfile) for p in profiles)
        
        # Check FP16 profile
        fp16_profile = next(p for p in profiles if p.precision == "fp16")
        assert fp16_profile.model_id == model_id
        assert fp16_profile.memory_requirement_gb == 20.0
        assert fp16_profile.precision == "fp16"
    
    def test_generate_all_profiles(self, generator):
        """Test generating profiles for all models."""
        all_profiles = generator.generate_all_profiles()
        
        assert len(all_profiles) > 0
        
        # Check that each model has profiles
        for model_id, profiles in all_profiles.items():
            assert len(profiles) > 0
            assert all(p.model_id == model_id for p in profiles)
    
    def test_profile_structure(self, generator):
        """Test that generated profiles have correct structure."""
        all_profiles = generator.generate_all_profiles()
        
        # Get first profile
        first_model = list(all_profiles.keys())[0]
        first_profile = all_profiles[first_model][0]
        
        # Check required fields
        assert hasattr(first_profile, 'model_id')
        assert hasattr(first_profile, 'variant_id')
        assert hasattr(first_profile, 'version')
        assert hasattr(first_profile, 'precision')
        assert hasattr(first_profile, 'memory_requirement_gb')
        assert hasattr(first_profile, 'gpu_sharing')
        assert hasattr(first_profile, 'resource_requirements')
        assert hasattr(first_profile, 'metadata')
    
    def test_profile_gpu_sharing_config(self, generator):
        """Test GPU sharing configuration in profiles."""
        all_profiles = generator.generate_all_profiles()
        
        # Get a profile
        first_model = list(all_profiles.keys())[0]
        profile = all_profiles[first_model][0]
        
        assert profile.gpu_sharing["enabled"] is True
        assert "memory_limit_gb" in profile.gpu_sharing
        assert "partition_id" in profile.gpu_sharing
        
        # Verify partition mode information is included
        assert "compute_mode" in profile.gpu_sharing, "compute_mode should be in gpu_sharing"
        assert "memory_mode" in profile.gpu_sharing, "memory_mode should be in gpu_sharing"
        assert "partition_count" in profile.gpu_sharing, "partition_count should be in gpu_sharing"
        assert "partition_size_gb" in profile.gpu_sharing, "partition_size_gb should be in gpu_sharing"
        
        # Verify compute_mode is valid (SPX or CPX)
        assert profile.gpu_sharing["compute_mode"] in ["SPX", "CPX"], \
            f"compute_mode should be SPX or CPX, got {profile.gpu_sharing['compute_mode']}"
        
        # Verify memory_mode is valid (NPS1 or NPS4)
        assert profile.gpu_sharing["memory_mode"] in ["NPS1", "NPS4"], \
            f"memory_mode should be NPS1 or NPS4, got {profile.gpu_sharing['memory_mode']}"
        
        # Verify partition_count matches compute_mode
        if profile.gpu_sharing["compute_mode"] == "CPX":
            assert profile.gpu_sharing["partition_count"] == 8, \
                "CPX mode should have 8 partitions"
        elif profile.gpu_sharing["compute_mode"] == "SPX":
            assert profile.gpu_sharing["partition_count"] == 1, \
                "SPX mode should have 1 partition"
        
        # Verify partition_config in metadata
        assert "partition_config" in profile.metadata, \
            "partition_config should be in metadata"
        partition_config = profile.metadata["partition_config"]
        assert partition_config["compute_mode"] == profile.gpu_sharing["compute_mode"]
        assert partition_config["memory_mode"] == profile.gpu_sharing["memory_mode"]
        assert partition_config["partition_count"] == profile.gpu_sharing["partition_count"]
        assert "qos_priority" in profile.gpu_sharing
    
    def test_save_profile(self, generator, tmp_path):
        """Test saving a profile to file."""
        model_id = "test/model"
        variants = [
            PrecisionVariant(precision="fp16", memory_gb=20.0, recommended_partition_gb=25.0)
        ]
        
        profiles = generator.generate_profiles_for_model(model_id, variants)
        profile = profiles[0]
        
        profile_path = generator.save_profile(profile, tmp_path)
        
        assert profile_path.exists()
        
        # Verify JSON content
        with open(profile_path) as f:
            data = json.load(f)
        
        assert data["model_id"] == model_id
        assert data["precision"] == "fp16"
        assert data["memory_requirement_gb"] == 20.0
    
    def test_save_all_profiles(self, generator, tmp_path):
        """Test saving all profiles."""
        generator.generate_all_profiles()
        
        saved_paths = generator.save_all_profiles(tmp_path)
        
        assert len(saved_paths) > 0
        assert all(Path(p).exists() for p in saved_paths)
    
    def test_get_profile(self, generator):
        """Test retrieving a profile by variant ID."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        variants = [
            PrecisionVariant(precision="fp16", memory_gb=20.0, recommended_partition_gb=25.0)
        ]
        
        generator.generate_profiles_for_model(model_id, variants)
        
        variant_id = f"{model_id}-fp16"
        profile = generator.get_profile(variant_id)
        
        assert profile is not None
        assert profile.variant_id == variant_id
    
    def test_list_profiles(self, generator):
        """Test listing all profile variant IDs."""
        generator.generate_all_profiles()
        
        variant_ids = generator.list_profiles()
        
        assert len(variant_ids) > 0
        assert all("-fp16" in vid or "-int8" in vid or "-int4" in vid for vid in variant_ids)


class TestPrecisionVariant:
    """Tests for PrecisionVariant dataclass."""
    
    def test_precision_variant_creation(self):
        """Test creating PrecisionVariant instance."""
        variant = PrecisionVariant(
            precision="fp16",
            memory_gb=20.0,
            recommended_partition_gb=25.0
        )
        
        assert variant.precision == "fp16"
        assert variant.memory_gb == 20.0
        assert variant.recommended_partition_gb == 25.0


class TestAIMProfile:
    """Tests for AIMProfile dataclass."""
    
    def test_aim_profile_creation(self):
        """Test creating AIMProfile instance."""
        profile = AIMProfile(
            model_id="test/model",
            variant_id="test/model-fp16",
            version="1.0.0-fp16",
            parameters="8B",
            precision="fp16",
            memory_requirement_gb=20.0,
            recommended_partition_gb=25.0,
            gpu_sharing={"enabled": True},
            resource_requirements={"gpu_memory_gb": 20.0},
            metadata={"quantization": "fp16"}
        )
        
        assert profile.model_id == "test/model"
        assert profile.variant_id == "test/model-fp16"
        assert profile.precision == "fp16"
        assert profile.memory_requirement_gb == 20.0

