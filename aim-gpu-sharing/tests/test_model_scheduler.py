"""
Unit tests for model scheduler.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from model_scheduler import ModelScheduler, ModelInstance, ModelStatus
from rocm_partitioner import ROCmPartitioner
from model_sizing import ModelSizingConfig


class TestModelScheduler:
    """Tests for ModelScheduler class."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing."""
        partitioner = ROCmPartitioner(gpu_id=0)
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
        return ModelScheduler(partitioner)
    
    def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler is not None
        assert scheduler.partitioner is not None
        assert len(scheduler.models) == 0
    
    def test_schedule_model(self, scheduler):
        """Test scheduling a model."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        success, partition_id, error = scheduler.schedule_model(model_id)
        
        assert success is True
        assert partition_id is not None
        assert error is None
        assert model_id in scheduler.models
    
    def test_schedule_model_with_priority(self, scheduler):
        """Test scheduling model with priority."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        success, partition_id, error = scheduler.schedule_model(
            model_id,
            priority=10
        )
        
        assert success is True
        instance = scheduler.get_model_info(model_id)
        assert instance.priority == 10
    
    def test_schedule_model_preferred_partition(self, scheduler):
        """Test scheduling model to preferred partition."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        success, partition_id, error = scheduler.schedule_model(
            model_id,
            preferred_partition=1
        )
        
        assert success is True
        assert partition_id == 1
    
    def test_schedule_model_no_available_partition(self, scheduler):
        """Test scheduling fails when no partition available."""
        # Fill all partitions with large models
        large_models = [
            "mistralai/Mistral-Small-3.1-24B",
            "mistralai/Mistral-Small-3.1-24B",
            "mistralai/Mistral-Small-3.1-24B",
            "mistralai/Mistral-Small-3.1-24B",
        ]
        
        for model_id in large_models:
            scheduler.schedule_model(model_id)
        
        # Try to schedule another model
        success, partition_id, error = scheduler.schedule_model(
            "meta-llama/Llama-3.1-8B-Instruct"
        )
        
        assert success is False
        assert "No suitable partition" in error
    
    def test_unschedule_model(self, scheduler):
        """Test unscheduling a model."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        scheduler.schedule_model(model_id)
        
        success = scheduler.unschedule_model(model_id)
        
        assert success is True
        assert model_id not in scheduler.models
    
    def test_unschedule_model_not_found(self, scheduler):
        """Test unscheduling non-existent model."""
        success = scheduler.unschedule_model("non-existent")
        assert success is False
    
    def test_update_model_status(self, scheduler):
        """Test updating model status."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        scheduler.schedule_model(model_id)
        
        success = scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        
        assert success is True
        instance = scheduler.get_model_info(model_id)
        assert instance.status == ModelStatus.RUNNING
    
    def test_get_model_info(self, scheduler):
        """Test retrieving model information."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        scheduler.schedule_model(model_id)
        
        instance = scheduler.get_model_info(model_id)
        
        assert instance is not None
        assert instance.model_id == model_id
        assert instance.status == ModelStatus.SCHEDULED
    
    def test_get_partition_models(self, scheduler):
        """Test getting models on a partition."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        success, partition_id, _ = scheduler.schedule_model(model_id)
        
        models = scheduler.get_partition_models(partition_id)
        
        assert model_id in models
    
    def test_get_scheduled_models(self, scheduler):
        """Test getting list of scheduled models."""
        model_ids = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-Small-3.1-24B",
        ]
        
        for model_id in model_ids:
            scheduler.schedule_model(model_id)
        
        scheduled = scheduler.get_scheduled_models()
        
        assert len(scheduled) == 2
        assert all(mid in scheduled for mid in model_ids)
    
    def test_get_running_models(self, scheduler):
        """Test getting list of running models."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        scheduler.schedule_model(model_id)
        scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        
        running = scheduler.get_running_models()
        
        assert model_id in running
        assert len(running) == 1
    
    def test_validate_schedule(self, scheduler):
        """Test validating schedule."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        scheduler.schedule_model(model_id)
        
        is_valid, errors = scheduler.validate_schedule()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_schedule_duplicate_model(self, scheduler):
        """Test scheduling same model twice."""
        model_id = "meta-llama/Llama-3.1-8B-Instruct"
        
        success1, partition1, _ = scheduler.schedule_model(model_id)
        success2, partition2, error2 = scheduler.schedule_model(model_id)
        
        assert success1 is True
        assert success2 is True  # Should return existing
        assert partition1 == partition2


class TestModelInstance:
    """Tests for ModelInstance dataclass."""
    
    def test_model_instance_creation(self):
        """Test creating ModelInstance."""
        instance = ModelInstance(
            model_id="test/model",
            partition_id=0,
            status=ModelStatus.SCHEDULED,
            memory_allocated_gb=20.0,
            priority=5
        )
        
        assert instance.model_id == "test/model"
        assert instance.partition_id == 0
        assert instance.status == ModelStatus.SCHEDULED
        assert instance.memory_allocated_gb == 20.0
        assert instance.priority == 5

