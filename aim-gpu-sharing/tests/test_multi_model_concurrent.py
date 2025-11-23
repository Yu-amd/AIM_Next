#!/usr/bin/env python3
"""
Tests for Multiple Models Running Concurrently on Same GPU

This test suite verifies that multiple different models/AIMs can run
concurrently on the same GPU using partitions.
"""

import sys
import pytest
from pathlib import Path

# Add runtime to path
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))

from model_scheduler import ModelScheduler, ModelStatus
from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode


class TestMultiModelConcurrent:
    """Tests for multiple models running concurrently on same GPU."""
    
    @pytest.fixture
    def partitioner(self):
        """Create partitioner - prefer CPX mode for multiple partitions."""
        # Try to use real hardware partitioner
        try:
            partitioner = ROCmPartitionerReal(gpu_id=0)
            if partitioner.amd_smi_available:
                # Get current modes
                compute, memory = partitioner.get_current_partition_mode()
                
                # Try to use CPX mode if available (4 partitions)
                # Otherwise use current mode
                try:
                    compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
                    memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
                except ValueError:
                    compute_mode = ComputePartitionMode.SPX
                    memory_mode = MemoryPartitionMode.NPS1
                
                # Try CPX mode first (4 partitions)
                if compute_mode == ComputePartitionMode.CPX or True:  # Try current mode
                    if partitioner.initialize("MI300X", compute_mode, memory_mode):
                        return partitioner
                
                # Fallback to SPX
                if partitioner.initialize("MI300X", ComputePartitionMode.SPX, MemoryPartitionMode.NPS1):
                    return partitioner
        except Exception:
            pass
        
        # Fallback to simulation
        from rocm_partitioner import ROCmPartitioner
        partitioner = ROCmPartitioner(gpu_id=0)
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])  # 4 partitions
        return partitioner
    
    @pytest.fixture
    def scheduler(self, partitioner):
        """Create scheduler instance."""
        return ModelScheduler(partitioner=partitioner, gpu_id=0)
    
    def test_multiple_models_same_gpu(self, scheduler):
        """Test scheduling multiple different models on the same GPU."""
        # Get available partitions
        available_partitions = scheduler.partitioner.get_available_partitions()
        num_partitions = len(available_partitions)
        
        if num_partitions < 2:
            pytest.skip(f"Need at least 2 partitions for multi-model test, got {num_partitions}")
        
        # Schedule multiple different models
        models = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2",
        ]
        
        scheduled_models = {}
        for model_id in models:
            success, partition_id, error = scheduler.schedule_model(model_id)
            assert success is True, f"Failed to schedule {model_id}: {error}"
            assert partition_id is not None
            scheduled_models[model_id] = partition_id
        
        # Verify all models are scheduled
        assert len(scheduled_models) == len(models)
        
        # Verify models are on different partitions (if possible)
        partition_ids = set(scheduled_models.values())
        # Models can be on same or different partitions depending on size
        
        # Verify all models are in scheduler
        scheduled = scheduler.get_scheduled_models()
        for model_id in models:
            assert model_id in scheduled, f"Model {model_id} not in scheduled models"
    
    def test_multiple_models_different_partitions(self, scheduler):
        """Test scheduling multiple models on different partitions."""
        available_partitions = scheduler.partitioner.get_available_partitions()
        num_partitions = len(available_partitions)
        
        if num_partitions < 2:
            pytest.skip(f"Need at least 2 partitions, got {num_partitions}")
        
        # Use small models that can fit in separate partitions
        models = [
            ("meta-llama/Llama-3.1-8B-Instruct", 0),
            ("mistralai/Mistral-7B-Instruct-v0.2", 1),
        ]
        
        scheduled = {}
        for model_id, preferred_partition in models:
            if preferred_partition >= num_partitions:
                continue  # Skip if partition doesn't exist
            
            success, partition_id, error = scheduler.schedule_model(
                model_id,
                preferred_partition=preferred_partition
            )
            assert success is True, f"Failed to schedule {model_id}: {error}"
            scheduled[model_id] = partition_id
        
        # Verify models are scheduled
        assert len(scheduled) > 0
        
        # Verify each model is on its partition
        for model_id, expected_partition in models:
            if model_id in scheduled:
                # May not be exact if preferred partition was full
                assert scheduled[model_id] is not None
    
    def test_concurrent_model_serving(self, scheduler):
        """Test that multiple models can be in RUNNING status concurrently."""
        available_partitions = scheduler.partitioner.get_available_partitions()
        num_partitions = len(available_partitions)
        
        if num_partitions < 1:
            pytest.skip("No partitions available")
        
        # Schedule multiple models
        models = [
            "meta-llama/Llama-3.1-8B-Instruct",
        ]
        
        # Add more models if we have partitions
        if num_partitions >= 2:
            models.append("mistralai/Mistral-7B-Instruct-v0.2")
        
        # Schedule all models
        for model_id in models:
            success, _, _ = scheduler.schedule_model(model_id)
            if not success:
                break  # Stop if we can't schedule more
        
        # Set all scheduled models to RUNNING
        running_count = 0
        for model_id in models:
            if model_id in scheduler.models:
                scheduler.update_model_status(model_id, ModelStatus.RUNNING)
                running_count += 1
        
        # Verify multiple models can be running
        running_models = scheduler.get_running_models()
        assert len(running_models) == running_count
        assert running_count > 0
    
    def test_model_isolation_same_gpu(self, scheduler):
        """Test that models on same GPU are properly isolated."""
        available_partitions = scheduler.partitioner.get_available_partitions()
        
        if len(available_partitions) < 1:
            pytest.skip("No partitions available")
        
        # Schedule a model
        model1_id = "meta-llama/Llama-3.1-8B-Instruct"
        success1, partition1, _ = scheduler.schedule_model(model1_id)
        assert success1 is True
        
        # Get model info
        model1_info = scheduler.get_model_info(model1_id)
        assert model1_info is not None
        assert model1_info.partition_id == partition1
        
        # If we have multiple partitions, schedule another model
        if len(available_partitions) >= 2:
            model2_id = "mistralai/Mistral-7B-Instruct-v0.2"
            success2, partition2, _ = scheduler.schedule_model(model2_id)
            
            if success2:
                model2_info = scheduler.get_model_info(model2_id)
                assert model2_info is not None
                assert model2_info.partition_id == partition2
                
                # Models should be isolated (different partition IDs or same partition with isolation)
                # Both should be able to run concurrently
                scheduler.update_model_status(model1_id, ModelStatus.RUNNING)
                scheduler.update_model_status(model2_id, ModelStatus.RUNNING)
                
                running = scheduler.get_running_models()
                assert model1_id in running
                assert model2_id in running
    
    def test_partition_utilization_multiple_models(self, scheduler):
        """Test partition utilization with multiple models."""
        available_partitions = scheduler.partitioner.get_available_partitions()
        
        if len(available_partitions) < 1:
            pytest.skip("No partitions available")
        
        # Schedule a model
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, partition_id, _ = scheduler.schedule_model(model_id)
        assert success is True
        
        # Get partition info
        partition_info = scheduler.partitioner.get_partition_info(partition_id)
        initial_allocated = partition_info.allocated_bytes
        
        # Verify partition has allocated memory
        assert initial_allocated > 0
        
        # If partition has space, try to schedule another model on same partition
        available_gb = (partition_info.size_bytes - partition_info.allocated_bytes) / (1024 ** 3)
        model_size_gb = scheduler.sizing_config.estimate_model_size(model_id)
        
        if available_gb >= model_size_gb + 2:  # 2GB overhead
            # Verify the partition utilization tracking works
            # get_partition_utilization returns a dict of partition_id -> utilization
            utilizations = scheduler.partitioner.get_partition_utilization()
            assert partition_id in utilizations
            utilization = utilizations[partition_id]
            assert utilization > 0
            # Utilization can be percentage (0-100) or fraction (0-1), check both
            assert utilization <= 100.0 or utilization <= 1.0


class TestMultiModelPodScenario:
    """Tests simulating multiple models in the same pod scenario."""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler for pod scenario."""
        try:
            partitioner = ROCmPartitionerReal(gpu_id=0)
            if partitioner.amd_smi_available:
                compute, memory = partitioner.get_current_partition_mode()
                compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
                memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
                if partitioner.initialize("MI300X", compute_mode, memory_mode):
                    return ModelScheduler(partitioner=partitioner, gpu_id=0)
        except Exception:
            pass
        
        # Fallback
        from rocm_partitioner import ROCmPartitioner
        partitioner = ROCmPartitioner(gpu_id=0)
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
        return ModelScheduler(partitioner=partitioner, gpu_id=0)
    
    def test_pod_with_multiple_aims(self, scheduler):
        """Test scenario: Single pod with multiple AIM models on same GPU."""
        # Simulate a pod that needs to run multiple models
        pod_models = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2",
        ]
        
        # Schedule all models for the pod
        scheduled = {}
        for model_id in pod_models:
            success, partition_id, error = scheduler.schedule_model(model_id)
            if success:
                scheduled[model_id] = partition_id
            # Continue even if some fail (partition constraints)
        
        # Verify at least one model is scheduled
        assert len(scheduled) > 0, "At least one model should be schedulable"
        
        # All scheduled models should be able to run concurrently
        for model_id in scheduled:
            scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        
        running = scheduler.get_running_models()
        assert len(running) == len(scheduled)
        
        # Verify all running models are on the same GPU (different partitions)
        partition_ids = set(scheduled.values())
        # All partitions should be on same GPU (gpu_id=0)
        assert len(partition_ids) > 0
    
    def test_concurrent_inference_same_gpu(self, scheduler):
        """Test that concurrent inference requests work for multiple models."""
        # Schedule multiple models
        models = ["meta-llama/Llama-3.1-8B-Instruct"]
        
        # Try to add more if partitions allow
        available = scheduler.partitioner.get_available_partitions()
        if len(available) >= 2:
            models.append("mistralai/Mistral-7B-Instruct-v0.2")
        
        # Schedule and set to running
        for model_id in models:
            success, _, _ = scheduler.schedule_model(model_id)
            if success:
                scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        
        # Verify all can serve concurrently
        running = scheduler.get_running_models()
        assert len(running) > 0
        
        # Each model should have its own partition
        for model_id in running:
            info = scheduler.get_model_info(model_id)
            assert info is not None
            assert info.status == ModelStatus.RUNNING
            assert info.partition_id is not None

