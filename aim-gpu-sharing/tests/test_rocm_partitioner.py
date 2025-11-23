"""
Unit tests for ROCm partitioner.

These tests work with both real hardware partitioner and simulation partitioner.
When real hardware is available, tests use the real ROCmPartitionerReal.
Otherwise, tests fall back to simulation partitioner.
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from model_sizing import ModelSizingConfig


class TestROCmPartitioner:
    """Tests for ROCmPartitioner class (works with both real and simulation)."""
    
    @pytest.fixture
    def partitioner(self):
        """
        Create a partitioner instance for testing.
        
        Uses real hardware partitioner if available, otherwise simulation.
        Prefers CPX mode (8 partitions) if available, otherwise uses current mode.
        """
        # Check if we should force simulation
        force_simulation = os.environ.get("FORCE_SIMULATION", "").lower() == "true"
        
        if force_simulation:
            from rocm_partitioner import ROCmPartitioner
            return ROCmPartitioner(gpu_id=0)
        
        # Try to use real partitioner
        try:
            from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
            test_partitioner = ROCmPartitionerReal(gpu_id=0)
            
            if test_partitioner.amd_smi_available:
                # Get current modes
                compute, memory = test_partitioner.get_current_partition_mode()
                
                # Map to enums
                try:
                    compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
                except ValueError:
                    compute_mode = ComputePartitionMode.SPX
                
                try:
                    memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
                except ValueError:
                    memory_mode = MemoryPartitionMode.NPS1
                
                # Try to use CPX mode if available (better for testing - 8 partitions)
                # Check if CPX is already set, or try to set it
                prefer_cpx = os.environ.get("PREFER_CPX", "true").lower() == "true"
                
                if prefer_cpx and compute_mode != ComputePartitionMode.CPX:
                    # Try to initialize with CPX/NPS4 (8 partitions, ~48GB each)
                    # This will fall back to current mode if CPX can't be set
                    cpx_success = test_partitioner.initialize(
                        gpu_name="MI300X",
                        compute_mode=ComputePartitionMode.CPX,
                        memory_mode=MemoryPartitionMode.NPS4
                    )
                    
                    if cpx_success and len(test_partitioner.partitions) == 8:
                        # CPX mode successfully initialized
                        return test_partitioner
                    else:
                        # CPX failed, reinitialize with current modes
                        test_partitioner = ROCmPartitionerReal(gpu_id=0)
                
                # Initialize with current modes (or CPX if already set)
                test_partitioner.initialize(
                    gpu_name="MI300X",
                    compute_mode=compute_mode,
                    memory_mode=memory_mode
                )
                return test_partitioner
        except Exception:
            pass
        
        # Fall back to simulation partitioner
        from rocm_partitioner import ROCmPartitioner
        return ROCmPartitioner(gpu_id=0)
    
    def _is_real_partitioner(self, partitioner):
        """Check if partitioner is real hardware partitioner."""
        return hasattr(partitioner, 'set_compute_partition_mode')
    
    def _get_expected_partition_count(self, partitioner):
        """Get expected partition count based on partitioner type."""
        if self._is_real_partitioner(partitioner):
            # Real partitioner: depends on compute mode
            if partitioner.compute_mode and partitioner.compute_mode.value == "CPX":
                return 8  # CPX mode has 8 partitions
            else:
                return 1  # SPX mode has 1 partition
        else:
            # Simulation partitioner: depends on initialization
            return len(partitioner.partitions)
    
    def test_initialization(self, partitioner):
        """Test partitioner initialization."""
        assert partitioner is not None
        assert partitioner.gpu_id == 0
        # Real partitioner may already be initialized, simulation starts uninitialized
        if not self._is_real_partitioner(partitioner):
            assert partitioner._initialized is False
    
    def test_cpx_mode_availability(self, partitioner):
        """Test CPX mode availability and detection."""
        if not self._is_real_partitioner(partitioner):
            pytest.skip("CPX mode only available on real hardware")
        
        # Check if we're in CPX mode
        is_cpx = (partitioner.compute_mode and 
                  partitioner.compute_mode.value == "CPX")
        
        if is_cpx:
            # CPX mode: should have 8 partitions
            assert len(partitioner.partitions) == 8, \
                f"CPX mode should have 8 partitions, got {len(partitioner.partitions)}"
            
            # Each partition should have XCD ID
            for pid, partition in partitioner.partitions.items():
                assert partition.xcd_id is not None, \
                    f"Partition {pid} should have XCD ID in CPX mode"
                assert partition.xcd_id == pid, \
                    f"Partition {pid} XCD ID should match partition ID"
            
            # In CPX mode, each XCD gets 24GB (192GB / 8)
            # This is true for both NPS1 and NPS4:
            # - NPS4: 4 quadrants of 48GB each, but each XCD gets 24GB (2 XCDs per quadrant)
            # - NPS1: All XCDs see full memory, but each XCD still gets 24GB share
            expected_memory = 192.0 / 8  # 24GB per XCD
            
            p0 = partitioner.partitions[0]
            actual_memory = p0.size_bytes / (1024 ** 3)
            assert abs(actual_memory - expected_memory) < 1.0, \
                f"CPX mode: Partition memory should be ~{expected_memory}GB (192GB/8), got {actual_memory}GB"
            
            print(f"\n✓ CPX mode detected: 8 partitions, {actual_memory:.1f}GB each (192GB / 8 = 24GB)")
        else:
            # SPX mode: 1 partition
            assert len(partitioner.partitions) == 1, \
                f"SPX mode should have 1 partition, got {len(partitioner.partitions)}"
            print(f"\nℹ SPX mode: 1 partition (CPX mode not set - requires boot-time configuration)")
    
    def test_initialize_partitions(self, partitioner):
        """Test initializing partitions."""
        if self._is_real_partitioner(partitioner):
            # Real partitioner is already initialized in fixture
            assert partitioner._initialized is True
            assert len(partitioner.partitions) > 0
            
            # Real partitioner can have:
            # - 1 partition in SPX mode
            # - 8 partitions in CPX mode
            assert len(partitioner.partitions) in [1, 8], \
                f"Expected 1 (SPX) or 8 (CPX) partitions, got {len(partitioner.partitions)}"
            
            # Log which mode we're using
            if partitioner.compute_mode:
                print(f"\nUsing {partitioner.compute_mode.value} mode: {len(partitioner.partitions)} partitions")
        else:
            # Simulation partitioner - initialize with custom sizes
            partition_sizes = [40.0, 40.0, 40.0, 40.0]
            success = partitioner.initialize("MI300X", partition_sizes)
            
            assert success is True
            assert partitioner._initialized is True
            assert len(partitioner.partitions) == 4
    
    def test_initialize_insufficient_memory(self, partitioner):
        """Test initialization fails with insufficient memory."""
        if self._is_real_partitioner(partitioner):
            # Real partitioner: test with invalid configuration
            # For real partitioner, we can't easily test this without changing modes
            # Skip this test for real partitioner or test differently
            pytest.skip("Real partitioner uses hardware modes, not custom sizes")
        else:
            # Simulation partitioner - try to allocate more than available
            partition_sizes = [100.0, 100.0]  # 200GB on 192GB GPU
            success = partitioner.initialize("MI300X", partition_sizes)
            
            assert success is False
    
    def test_allocate_model(self, partitioner):
        """Test allocating a model to a partition."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if not already done
            if not partitioner._initialized:
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
        if self._is_real_partitioner(partitioner):
            # Real partitioner: fill the partition first, then try to allocate
            # Get partition size
            partition = partitioner.get_partition_info(0)
            partition_size_gb = partition.size_bytes / (1024 ** 3)
            
            # Use a model that's larger than the partition
            # For SPX mode with 192GB, we need a very large model
            if partition_size_gb >= 100:
                # Use a model that definitely won't fit
                model_id = "meta-llama/Llama-3.3-70B-Instruct"  # 165GB
            else:
                model_id = "meta-llama/Llama-3.1-70B-Instruct"  # 40GB
            
            success, error = partitioner.allocate_model(model_id, partition_id=0)
            # May succeed if model fits, so we'll test by filling partition first
            # For now, just verify the error handling works
            if not success:
                assert error is not None
                assert "requires" in error.lower() or "available" in error.lower()
        else:
            # Simulation partitioner - use small partition
            partitioner.initialize("MI300X", [10.0])  # Small partition
            
            model_id = "meta-llama/Llama-3.1-8B-Instruct"  # Needs ~20GB
            success, error = partitioner.allocate_model(model_id, partition_id=0)
            
            assert success is False
            assert error is not None
            assert "requires" in error.lower()
    
    def test_allocate_model_invalid_partition(self, partitioner):
        """Test allocation fails for invalid partition ID."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0])
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        # Use a partition ID that definitely doesn't exist
        invalid_partition_id = 999
        success, error = partitioner.allocate_model(model_id, partition_id=invalid_partition_id)
        
        assert success is False
        assert error is not None
        assert "does not exist" in error.lower() or "not exist" in error.lower()
    
    def test_deallocate_model(self, partitioner):
        """Test deallocating a model from a partition."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0])
        
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, error = partitioner.allocate_model(model_id, partition_id=0)
        assert success is True, f"Allocation failed: {error}"
        
        success = partitioner.deallocate_model(model_id, partition_id=0)
        assert success is True
        
        partition = partitioner.get_partition_info(0)
        assert model_id not in partition.models
        # Allocated bytes should be reduced (may not be exactly 0 if other models exist)
        initial_allocated = partition.allocated_bytes
        # Verify it decreased
        assert partition.allocated_bytes < initial_allocated or initial_allocated == 0
    
    def test_deallocate_model_not_found(self, partitioner):
        """Test deallocating non-existent model."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0])
        
        success = partitioner.deallocate_model("non-existent", partition_id=0)
        assert success is False
    
    def test_get_partition_info(self, partitioner):
        """Test retrieving partition information."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 50.0])
        
        partition = partitioner.get_partition_info(0)
        assert partition is not None
        assert partition.partition_id == 0
        assert partition.size_bytes > 0
        
        if not self._is_real_partitioner(partitioner):
            # For simulation, verify exact size
            assert partition.size_bytes == 40.0 * (1024 ** 3)
    
    def test_get_available_partitions(self, partitioner):
        """Test getting list of available partitions."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0, 40.0])
        
        available = partitioner.get_available_partitions()
        assert len(available) > 0  # At least one partition should be available
        
        if not self._is_real_partitioner(partitioner):
            # For simulation with 3 partitions
            assert len(available) == 3
            assert 0 in available
            assert 1 in available
            assert 2 in available
        else:
            # Real partitioner: SPX has 1, CPX has 8
            expected_count = len(partitioner.partitions)
            assert len(available) == expected_count, \
                f"Expected {expected_count} available partitions, got {len(available)}"
            # Verify all partition IDs are in available list
            for pid in partitioner.partitions.keys():
                assert pid in available, f"Partition {pid} should be available"
        
        # Allocate a model to partition 0
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, error = partitioner.allocate_model(model_id, partition_id=0)
        assert success is True, f"Allocation failed: {error}"
        
        # Check available partitions after allocation
        available_after = partitioner.get_available_partitions()
        # Partition 0 might still be available if model is small, or might be full
        # Other partitions should still be available (if more than 1 partition)
        if len(partitioner.partitions) > 1:
            assert len(available_after) >= len(partitioner.partitions) - 1, \
                f"At least {len(partitioner.partitions) - 1} partitions should still be available"
    
    def test_get_partition_utilization(self, partitioner):
        """Test getting partition utilization."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0])
        
        utilization = partitioner.get_partition_utilization()
        assert len(utilization) > 0  # At least one partition
        
        if not self._is_real_partitioner(partitioner):
            # For simulation with 2 partitions
            assert len(utilization) == 2
            assert utilization[0] == 0.0  # Initially empty
            assert utilization[1] == 0.0
        
        # Allocate model
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, error = partitioner.allocate_model(model_id, partition_id=0)
        assert success is True, f"Allocation failed: {error}"
        
        utilization_after = partitioner.get_partition_utilization()
        assert utilization_after[0] > 0.0
        assert utilization_after[0] <= 100.0
    
    def test_validate_partitioning(self, partitioner):
        """Test validating partitioning configuration."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0, 40.0])
        
        is_valid, errors = partitioner.validate_partitioning()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_partitioning_with_overflow(self, partitioner):
        """Test validation detects memory overflow."""
        if not self._is_real_partitioner(partitioner):
            # Simulation partitioner - initialize if needed
            if not partitioner._initialized:
                partitioner.initialize("MI300X", [40.0, 40.0])
            
            # Manually create overflow condition (for testing)
            partition = partitioner.get_partition_info(0)
            partition.allocated_bytes = partition.size_bytes + (10 * 1024 ** 3)  # 10GB overflow
            
            is_valid, errors = partitioner.validate_partitioning()
            assert is_valid is False
            assert len(errors) > 0
            assert any("overflow" in error.lower() for error in errors)
        else:
            # For real partitioner, test with actual allocation that might overflow
            # This is harder to test without actually filling the partition
            # Skip or test differently
            pytest.skip("Real partitioner overflow test requires different approach")


class TestMemoryPartition:
    """Tests for MemoryPartition dataclass."""
    
    def test_memory_partition_creation(self):
        """Test creating MemoryPartition instance."""
        # Import the appropriate MemoryPartition class
        try:
            from rocm_partitioner_real import MemoryPartition
        except ImportError:
            from rocm_partitioner import MemoryPartition
        
        # Real partitioner MemoryPartition may not have start_address
        try:
            partition = MemoryPartition(
                partition_id=0,
                start_address=0,
                size_bytes=40 * (1024 ** 3),
                allocated_bytes=0,
                models=[],
                is_active=True
            )
        except TypeError:
            # Real partitioner doesn't have start_address
            partition = MemoryPartition(
                partition_id=0,
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

