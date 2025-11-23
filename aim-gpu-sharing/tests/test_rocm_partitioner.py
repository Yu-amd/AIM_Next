"""
Unit tests for ROCm partitioner.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from rocm_partitioner import ROCmPartitioner, MemoryPartition
from model_sizing import ModelSizingConfig


class TestROCmPartitioner:
    """Tests for ROCmPartitioner class."""
    
    @pytest.fixture
    def partitioner(self):
        """Create a partitioner instance for testing."""
        return ROCmPartitioner(gpu_id=0)
    
    def test_initialization(self, partitioner):
        """Test partitioner initialization."""
        assert partitioner is not None
        assert partitioner.gpu_id == 0
        assert partitioner._initialized is False
    
    def test_initialize_partitions(self, partitioner):
        """Test initializing partitions."""
        partition_sizes = [40.0, 40.0, 40.0, 40.0]
        success = partitioner.initialize("MI300X", partition_sizes)
        
        assert success is True
        assert partitioner._initialized is True
        assert len(partitioner.partitions) == 4
    
    def test_initialize_insufficient_memory(self, partitioner):
        """Test initialization fails with insufficient memory."""
        # Try to allocate more than available
        partition_sizes = [100.0, 100.0]  # 200GB on 192GB GPU
        success = partitioner.initialize("MI300X", partition_sizes)
        
        assert success is False
    
    def test_allocate_model(self, partitioner):
        """Test allocating a model to a partition."""
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, error = partitioner.allocate_model(model_id, partition_id=0)
        
        assert success is True
        assert error is None
        
        partition = partitioner.get_partition_info(0)
        assert model_id in partition.models
        assert partition.allocated_bytes > 0
    
    def test_allocate_model_insufficient_space(self, partitioner):
        """Test allocation fails when partition is too small."""
        partitioner.initialize("MI300X", [10.0])  # Small partition
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"  # Needs ~20GB
        success, error = partitioner.allocate_model(model_id, partition_id=0)
        
        assert success is False
        assert error is not None
        assert "requires" in error.lower()
    
    def test_allocate_model_invalid_partition(self, partitioner):
        """Test allocation fails for invalid partition ID."""
        partitioner.initialize("MI300X", [40.0, 40.0])
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, error = partitioner.allocate_model(model_id, partition_id=99)
        
        assert success is False
        assert "does not exist" in error.lower()
    
    def test_deallocate_model(self, partitioner):
        """Test deallocating a model from a partition."""
        partitioner.initialize("MI300X", [40.0, 40.0])
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        partitioner.allocate_model(model_id, partition_id=0)
        
        success = partitioner.deallocate_model(model_id, partition_id=0)
        assert success is True
        
        partition = partitioner.get_partition_info(0)
        assert model_id not in partition.models
        assert partition.allocated_bytes == 0
    
    def test_deallocate_model_not_found(self, partitioner):
        """Test deallocating non-existent model."""
        partitioner.initialize("MI300X", [40.0])
        
        success = partitioner.deallocate_model("non-existent", partition_id=0)
        assert success is False
    
    def test_get_partition_info(self, partitioner):
        """Test retrieving partition information."""
        partitioner.initialize("MI300X", [40.0, 50.0])
        
        partition = partitioner.get_partition_info(0)
        assert partition is not None
        assert partition.partition_id == 0
        assert partition.size_bytes == 40.0 * (1024 ** 3)
    
    def test_get_available_partitions(self, partitioner):
        """Test getting list of available partitions."""
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0])
        
        available = partitioner.get_available_partitions()
        assert len(available) == 3
        assert 0 in available
        assert 1 in available
        assert 2 in available
        
        # Allocate a model to partition 0
        partitioner.allocate_model("meta-llama/Llama-3.1-8B-Instruct", partition_id=0)
        
        # Partition 0 might still be available if model is small enough
        available_after = partitioner.get_available_partitions()
        assert len(available_after) >= 2  # At least 2 should still be available
    
    def test_get_partition_utilization(self, partitioner):
        """Test getting partition utilization."""
        partitioner.initialize("MI300X", [40.0, 40.0])
        
        utilization = partitioner.get_partition_utilization()
        assert len(utilization) == 2
        assert utilization[0] == 0.0  # Initially empty
        assert utilization[1] == 0.0
        
        # Allocate model
        partitioner.allocate_model("meta-llama/Llama-3.1-8B-Instruct", partition_id=0)
        
        utilization_after = partitioner.get_partition_utilization()
        assert utilization_after[0] > 0.0
        assert utilization_after[0] <= 100.0
    
    def test_validate_partitioning(self, partitioner):
        """Test validating partitioning configuration."""
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0])
        
        is_valid, errors = partitioner.validate_partitioning()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_partitioning_with_overflow(self, partitioner):
        """Test validation detects memory overflow."""
        partitioner.initialize("MI300X", [40.0, 40.0])
        
        # Manually create overflow condition (for testing)
        partition = partitioner.get_partition_info(0)
        partition.allocated_bytes = partition.size_bytes + (10 * 1024 ** 3)  # 10GB overflow
        
        is_valid, errors = partitioner.validate_partitioning()
        assert is_valid is False
        assert len(errors) > 0
        assert any("overflow" in error.lower() for error in errors)


class TestMemoryPartition:
    """Tests for MemoryPartition dataclass."""
    
    def test_memory_partition_creation(self):
        """Test creating MemoryPartition instance."""
        partition = MemoryPartition(
            partition_id=0,
            start_address=0,
            size_bytes=40 * (1024 ** 3),
            allocated_bytes=0,
            models=[],
            is_active=True
        )
        
        assert partition.partition_id == 0
        assert partition.size_bytes == 40 * (1024 ** 3)
        assert partition.allocated_bytes == 0
        assert len(partition.models) == 0
        assert partition.is_active is True

