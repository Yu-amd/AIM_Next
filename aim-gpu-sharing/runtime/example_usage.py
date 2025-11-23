"""
Example usage of GPU memory partitioning components.

This script demonstrates how to use the ROCm partitioner, model scheduler,
and resource isolator to manage multi-model deployment on a single GPU.
"""

import logging
from model_sizing import ModelSizingConfig
from rocm_partitioner import ROCmPartitioner
from model_scheduler import ModelScheduler, ModelStatus
from resource_isolator import ResourceIsolator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_partitioning():
    """Example: Basic memory partitioning setup."""
    logger.info("=== Example: Basic Memory Partitioning ===")
    
    # Initialize components
    sizing_config = ModelSizingConfig()
    partitioner = ROCmPartitioner(gpu_id=0)
    
    # Initialize partitions on MI300X (192GB)
    partition_sizes = [40.0, 40.0, 40.0, 40.0]  # 4 partitions of 40GB each
    success = partitioner.initialize("MI300X", partition_sizes)
    
    if not success:
        logger.error("Failed to initialize partitions")
        return
    
    logger.info("Partitions initialized successfully")
    
    # Get partition utilization
    utilization = partitioner.get_partition_utilization()
    for partition_id, util in utilization.items():
        logger.info(f"Partition {partition_id}: {util:.1f}% utilized")


def example_model_scheduling():
    """Example: Scheduling multiple models."""
    logger.info("=== Example: Model Scheduling ===")
    
    # Initialize components
    sizing_config = ModelSizingConfig()
    partitioner = ROCmPartitioner(gpu_id=0)
    
    # Initialize partitions
    partition_sizes = [50.0, 50.0, 50.0]  # 3 partitions
    partitioner.initialize("MI300X", partition_sizes)
    
    # Create scheduler
    scheduler = ModelScheduler(partitioner)
    
    # Schedule models (example model IDs - replace with actual models from config)
    models_to_schedule = [
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct",
        "Qwen/Qwen-7B-Chat",
    ]
    
    for model_id in models_to_schedule:
        success, partition_id, error = scheduler.schedule_model(model_id)
        if success:
            logger.info(
                f"Scheduled {model_id} on partition {partition_id}"
            )
            # Update status to running
            scheduler.update_model_status(model_id, ModelStatus.RUNNING)
        else:
            logger.error(f"Failed to schedule {model_id}: {error}")
    
    # List scheduled models
    scheduled = scheduler.get_scheduled_models()
    logger.info(f"Total scheduled models: {len(scheduled)}")
    
    # Validate schedule
    is_valid, errors = scheduler.validate_schedule()
    if is_valid:
        logger.info("Schedule validation passed")
    else:
        logger.error(f"Schedule validation failed: {errors}")


def example_optimal_partitioning():
    """Example: Calculate optimal partitions for models."""
    logger.info("=== Example: Optimal Partition Calculation ===")
    
    sizing_config = ModelSizingConfig()
    
    # Models to deploy
    model_ids = [
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct",
        "Qwen/Qwen-7B-Chat",
        "google/gemma-7b-it",
    ]
    
    try:
        # Calculate optimal partitions
        partitions = sizing_config.calculate_optimal_partitions(
            "MI300X",
            model_ids
        )
        
        logger.info(f"Optimal partition configuration:")
        for partition in partitions:
            logger.info(
                f"  Partition {partition['partition_id']}: "
                f"{len(partition['models'])} models, "
                f"{partition['allocated_gb']:.1f}GB allocated"
            )
            for model_id in partition['models']:
                logger.info(f"    - {model_id}")
    
    except ValueError as e:
        logger.error(f"Failed to calculate partitions: {e}")


def example_resource_isolation():
    """Example: Compute resource isolation."""
    logger.info("=== Example: Resource Isolation ===")
    
    isolator = ResourceIsolator(gpu_id=0)
    
    # Initialize with 4 partitions on MI300X (304 compute units)
    partition_ids = [0, 1, 2, 3]
    isolator.initialize(304, partition_ids)
    
    # Set custom limits for high-priority partition
    isolator.set_partition_limits(
        partition_id=0,
        max_units=100,
        min_units=80,
        priority=10
    )
    
    # Get environment variables for a partition
    env_vars = isolator.get_environment_variables(partition_id=0)
    logger.info(f"Environment variables for partition 0:")
    for key, value in env_vars.items():
        logger.info(f"  {key}={value}")
    
    # Validate limits
    is_valid, errors = isolator.validate_limits()
    if is_valid:
        logger.info("Resource isolation validation passed")
    else:
        logger.error(f"Validation failed: {errors}")


if __name__ == "__main__":
    # Run examples
    example_basic_partitioning()
    print()
    example_model_scheduling()
    print()
    example_optimal_partitioning()
    print()
    example_resource_isolation()

