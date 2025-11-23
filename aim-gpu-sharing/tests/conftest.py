"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
import os
from pathlib import Path

# Add runtime to path for imports
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))


@pytest.fixture(scope="session")
def test_config_path():
    """Path to test model sizing configuration."""
    return runtime_path / "model_sizing_config.yaml"


@pytest.fixture(scope="session")
def sample_model_id():
    """Sample model ID for testing."""
    return "meta-llama/Llama-3.1-8B-Instruct"


@pytest.fixture(scope="session")
def sample_gpu_name():
    """Sample GPU name for testing."""
    return "MI300X"


@pytest.fixture(scope="function")
def partitioner():
    """
    Create a partitioner instance for testing.
    
    Automatically selects real partitioner if hardware is available,
    otherwise uses simulation partitioner.
    """
    # Check if we should force simulation
    force_simulation = os.environ.get("FORCE_SIMULATION", "").lower() == "true"
    
    if force_simulation:
        from rocm_partitioner import ROCmPartitioner
        partitioner = ROCmPartitioner(gpu_id=0)
        partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
        return partitioner
    
    # Directly check for real hardware by testing ROCmPartitionerReal
    try:
        from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
        test_partitioner = ROCmPartitionerReal(gpu_id=0)
        
        if test_partitioner.amd_smi_available:
            # Use real partitioner
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
            
            # Initialize with current modes
            test_partitioner.initialize(
                gpu_name="MI300X",
                compute_mode=compute_mode,
                memory_mode=memory_mode
            )
            return test_partitioner
    except Exception as e:
        # Fall back to simulation if real partitioner fails
        pass
    
    # Fall back to simulation partitioner
    from rocm_partitioner import ROCmPartitioner
    partitioner = ROCmPartitioner(gpu_id=0)
    partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
    return partitioner

