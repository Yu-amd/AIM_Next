"""
Example: Automatic hardware detection and partitioner selection.

This example demonstrates how the system automatically detects
hardware and selects the appropriate partitioner implementation.
"""

import logging
from hardware_detector import HardwareDetector, get_partitioner_class
from auto_partitioner import create_partitioner, initialize_partitioner
from model_scheduler import ModelScheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_hardware_detection():
    """Example: Detect hardware capabilities."""
    logger.info("=== Hardware Detection Example ===")
    
    detector = HardwareDetector()
    
    # Detect amd-smi
    amd_smi_available = detector.detect_amd_smi()
    logger.info(f"amd-smi available: {amd_smi_available}")
    
    # Detect ROCm
    rocm_available = detector.detect_rocm()
    logger.info(f"ROCm available: {rocm_available}")
    
    # List available GPUs
    gpu_ids = detector.list_available_gpus()
    logger.info(f"Available GPUs: {gpu_ids}")
    
    # Detect each GPU
    for gpu_id in gpu_ids:
        info = detector.detect_gpu(gpu_id)
        capability = detector.get_capability(gpu_id)
        
        logger.info(f"\nGPU {gpu_id}:")
        logger.info(f"  Model: {info.model_name}")
        logger.info(f"  Supports partitioning: {info.supports_partitioning}")
        logger.info(f"  Capability: {capability.value}")


def example_auto_partitioner():
    """Example: Auto-select partitioner based on hardware."""
    logger.info("\n=== Auto Partitioner Example ===")
    
    # Automatically create partitioner (detects hardware)
    partitioner = create_partitioner(gpu_id=0)
    
    # Initialize with appropriate settings
    success = initialize_partitioner(
        partitioner,
        gpu_name="MI300X"
    )
    
    if success:
        logger.info("Partitioner initialized successfully")
        
        # Check partitioner type
        if hasattr(partitioner, 'get_logical_devices'):
            # Real partitioner
            devices = partitioner.get_logical_devices()
            logger.info(f"Created {len(devices)} logical devices")
            for device in devices:
                logger.info(
                    f"  Device {device['device_id']}: "
                    f"{device['memory_gb']:.1f}GB available"
                )
        else:
            # Simulation partitioner
            partitions = partitioner.get_available_partitions()
            logger.info(f"Created {len(partitions)} partitions")
    else:
        logger.error("Failed to initialize partitioner")


def example_auto_scheduler():
    """Example: Auto-detect and schedule models."""
    logger.info("\n=== Auto Scheduler Example ===")
    
    # Create scheduler with auto-detection
    scheduler = ModelScheduler(
        gpu_id=0,
        auto_detect=True  # Automatically detect hardware
    )
    
    # Initialize partitioner if needed (for simulation mode)
    if not hasattr(scheduler.partitioner, '_initialized') or not scheduler.partitioner._initialized:
        if hasattr(scheduler.partitioner, 'set_compute_partition_mode'):
            # Real partitioner - initialize with partition modes
            from rocm_partitioner_real import ComputePartitionMode, MemoryPartitionMode
            scheduler.partitioner.initialize(
                "MI300X",
                compute_mode=ComputePartitionMode.CPX,
                memory_mode=MemoryPartitionMode.NPS4
            )
        else:
            # Simulation partitioner - initialize with partition sizes
            scheduler.partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
    
    # Schedule models (works with both simulation and real)
    models = [
        "meta-llama/Llama-3.1-8B-Instruct",
    ]
    
    for model_id in models:
        success, partition_id, error = scheduler.schedule_model(
            model_id,
            precision="fp16"
        )
        
        if success:
            logger.info(
                f"Scheduled {model_id} on partition {partition_id}"
            )
            
            # Get environment variables for deployment
            env_vars = scheduler.get_partition_environment(partition_id)
            logger.info(f"  Environment: {env_vars}")
        else:
            logger.error(f"Failed to schedule {model_id}: {error}")


def example_force_simulation():
    """Example: Force simulation mode even with hardware."""
    logger.info("\n=== Force Simulation Example ===")
    
    # Force simulation mode
    partitioner = create_partitioner(
        gpu_id=0,
        force_simulation=True
    )
    
    # Initialize with manual partition sizes
    success = initialize_partitioner(
        partitioner,
        gpu_name="MI300X",
        partition_sizes_gb=[50.0, 50.0, 50.0, 42.0]  # Custom sizes
    )
    
    if success:
        logger.info("Simulation partitioner initialized with custom sizes")


if __name__ == "__main__":
    # Run examples
    example_hardware_detection()
    example_auto_partitioner()
    example_auto_scheduler()
    example_force_simulation()

