"""
Unit tests for resource isolator.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from resource_isolator import ResourceIsolator, ComputeLimits


class TestResourceIsolator:
    """Tests for ResourceIsolator class."""
    
    @pytest.fixture
    def isolator(self):
        """Create an isolator instance for testing."""
        return ResourceIsolator(gpu_id=0)
    
    def test_initialization(self, isolator):
        """Test isolator initialization."""
        assert isolator is not None
        assert isolator.gpu_id == 0
        assert isolator._initialized is False
    
    def test_initialize(self, isolator):
        """Test initializing compute isolation."""
        partition_ids = [0, 1, 2, 3]
        success = isolator.initialize(304, partition_ids)  # MI300X compute units
        
        assert success is True
        assert isolator._initialized is True
        assert len(isolator.compute_limits) == 4
    
    def test_initialize_already_initialized(self, isolator):
        """Test initialization fails when already initialized."""
        isolator.initialize(304, [0, 1])
        success = isolator.initialize(304, [0, 1])
        
        assert success is False
    
    def test_set_partition_limits(self, isolator):
        """Test setting compute limits for a partition."""
        isolator.initialize(304, [0, 1, 2])
        
        success = isolator.set_partition_limits(
            partition_id=0,
            max_units=100,
            min_units=80,
            priority=10
        )
        
        assert success is True
        
        limits = isolator.get_partition_limits(0)
        assert limits.max_compute_units == 100
        assert limits.min_compute_units == 80
        assert limits.priority == 10
    
    def test_set_partition_limits_invalid_partition(self, isolator):
        """Test setting limits for invalid partition."""
        isolator.initialize(304, [0, 1])
        
        success = isolator.set_partition_limits(partition_id=99, max_units=100)
        assert success is False
    
    def test_set_partition_limits_exceeds_total(self, isolator):
        """Test setting limits that exceed total compute units."""
        isolator.initialize(304, [0, 1])
        
        success = isolator.set_partition_limits(
            partition_id=0,
            max_units=500  # Exceeds 304
        )
        assert success is False
    
    def test_get_partition_limits(self, isolator):
        """Test retrieving partition limits."""
        isolator.initialize(304, [0, 1, 2])
        
        limits = isolator.get_partition_limits(0)
        
        assert limits is not None
        assert limits.partition_id == 0
        assert limits.max_compute_units is not None
    
    def test_get_environment_variables(self, isolator):
        """Test getting environment variables for partition."""
        isolator.initialize(304, [0, 1])
        
        env_vars = isolator.get_environment_variables(partition_id=0)
        
        assert "ROCR_VISIBLE_DEVICES" in env_vars
        assert "AIM_PARTITION_ID" in env_vars
        assert env_vars["AIM_PARTITION_ID"] == "0"
    
    def test_get_environment_variables_with_limits(self, isolator):
        """Test environment variables include compute limits."""
        isolator.initialize(304, [0, 1])
        isolator.set_partition_limits(0, max_units=100, min_units=80)
        
        env_vars = isolator.get_environment_variables(partition_id=0)
        
        assert "ROCM_MAX_COMPUTE_UNITS" in env_vars
        assert "ROCM_MIN_COMPUTE_UNITS" in env_vars
        assert env_vars["ROCM_MAX_COMPUTE_UNITS"] == "100"
        assert env_vars["ROCM_MIN_COMPUTE_UNITS"] == "80"
    
    def test_validate_limits(self, isolator):
        """Test validating compute limits."""
        isolator.initialize(304, [0, 1, 2])
        
        is_valid, errors = isolator.validate_limits()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_limits_exceeds_total(self, isolator):
        """Test validation fails when limits exceed total."""
        isolator.initialize(304, [0, 1])
        
        # Manually set invalid limits (for testing)
        limits = isolator.get_partition_limits(0)
        limits.min_compute_units = 200
        limits = isolator.get_partition_limits(1)
        limits.min_compute_units = 200  # Total: 400 > 304
        
        is_valid, errors = isolator.validate_limits()
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("exceeds" in error.lower() for error in errors)
    
    def test_validate_limits_min_greater_than_max(self, isolator):
        """Test validation fails when min > max."""
        isolator.initialize(304, [0])
        
        # Manually set invalid limits
        limits = isolator.get_partition_limits(0)
        limits.min_compute_units = 100
        limits.max_compute_units = 50
        
        is_valid, errors = isolator.validate_limits()
        
        assert is_valid is False
        assert any("min" in error.lower() and "max" in error.lower() for error in errors)


class TestComputeLimits:
    """Tests for ComputeLimits dataclass."""
    
    def test_compute_limits_creation(self):
        """Test creating ComputeLimits instance."""
        limits = ComputeLimits(
            partition_id=0,
            max_compute_units=100,
            min_compute_units=80,
            priority=5
        )
        
        assert limits.partition_id == 0
        assert limits.max_compute_units == 100
        assert limits.min_compute_units == 80
        assert limits.priority == 5
    
    def test_compute_limits_optional_fields(self):
        """Test ComputeLimits with optional fields."""
        limits = ComputeLimits(partition_id=0)
        
        assert limits.partition_id == 0
        assert limits.max_compute_units is None
        assert limits.min_compute_units is None
        assert limits.priority == 0

