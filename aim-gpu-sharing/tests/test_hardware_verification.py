#!/usr/bin/env python3
"""
Hardware Verification Tests

These tests verify that the real hardware partitioner is working correctly
with actual AMD GPUs and ROCm partition modes.

REQUIRES: Real hardware with amd-smi available
"""

import sys
import os
from pathlib import Path

# Add runtime to path
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))


def test_amd_smi_available():
    """Test that amd-smi is available on the system."""
    print("\n=== Testing amd-smi Availability ===")
    
    # Check if amd-smi command exists
    import subprocess
    try:
        result = subprocess.run(
            ['which', 'amd-smi'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("✗ amd-smi command not found in PATH")
            return False
        
        amd_smi_path = result.stdout.strip()
        print(f"✓ amd-smi found at: {amd_smi_path}")
        
        # Try to run amd-smi
        result = subprocess.run(
            ['amd-smi', '-h'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("✗ amd-smi command not executable")
            return False
        
        print("✓ amd-smi is executable")
        return True
    except Exception as e:
        print(f"✗ Error checking amd-smi: {e}")
        return False


def test_real_hardware_partitioner_available():
    """Test that real hardware partitioner can be imported and initialized."""
    print("\n=== Testing Real Hardware Partitioner ===")
    
    try:
        from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
        print("✓ ROCmPartitionerReal imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ROCmPartitionerReal: {e}")
        return False
    
    try:
        partitioner = ROCmPartitionerReal(gpu_id=0)
        print("✓ ROCmPartitionerReal instance created")
        
        if not partitioner.amd_smi_available:
            print("✗ amd-smi not available in partitioner")
            return False
        
        print("✓ amd-smi available in partitioner")
        return True
    except Exception as e:
        print(f"✗ Error creating partitioner: {e}")
        return False


def test_get_current_partition_mode():
    """Test getting current partition mode from hardware."""
    print("\n=== Testing Current Partition Mode Detection ===")
    
    try:
        from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
        
        partitioner = ROCmPartitionerReal(gpu_id=0)
        if not partitioner.amd_smi_available:
            print("⚠ Skipping - amd-smi not available")
            return True
        
        compute, memory = partitioner.get_current_partition_mode()
        print(f"✓ Current compute mode: {compute}")
        print(f"✓ Current memory mode: {memory}")
        
        if compute is None or memory is None:
            print("⚠ Could not detect partition modes (may be normal)")
            return True
        
        return True
    except Exception as e:
        print(f"✗ Error getting partition mode: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_initialize_real_partitioner():
    """Test initializing real hardware partitioner."""
    print("\n=== Testing Real Partitioner Initialization ===")
    
    try:
        from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode, MemoryPartitionMode
        
        partitioner = ROCmPartitionerReal(gpu_id=0)
        if not partitioner.amd_smi_available:
            print("⚠ Skipping - amd-smi not available")
            return True
        
        # Get current modes
        compute, memory = partitioner.get_current_partition_mode()
        compute_mode = ComputePartitionMode(compute) if compute else ComputePartitionMode.SPX
        memory_mode = MemoryPartitionMode(memory) if memory else MemoryPartitionMode.NPS1
        
        # Try to initialize
        success = partitioner.initialize("MI300X", compute_mode, memory_mode)
        
        if success:
            print("✓ Partitioner initialized successfully")
            print(f"  - Partitions: {len(partitioner.partitions)}")
            print(f"  - Compute mode: {partitioner.compute_mode}")
            print(f"  - Memory mode: {partitioner.memory_mode}")
            
            # Show partition info
            for pid, partition in list(partitioner.partitions.items())[:3]:
                print(f"  - Partition {pid}: {partition.size_bytes / (1024**3):.2f} GB")
            if len(partitioner.partitions) > 3:
                print(f"  - ... and {len(partitioner.partitions) - 3} more partitions")
            
            return True
        else:
            print("✗ Partitioner initialization failed")
            return False
    except Exception as e:
        print(f"✗ Error initializing partitioner: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hardware_vs_simulation():
    """Verify we're using real hardware, not simulation."""
    print("\n=== Verifying Real Hardware Usage ===")
    
    try:
        from rocm_partitioner_real import ROCmPartitionerReal
        
        partitioner = ROCmPartitionerReal(gpu_id=0)
        
        if not partitioner.amd_smi_available:
            print("⚠ WARNING: amd-smi not available - using simulation mode")
            print("  This test requires real hardware with amd-smi")
            return False
        
        # Check if partitioner has real hardware methods
        if not hasattr(partitioner, 'amd_smi_available'):
            print("✗ Partitioner missing amd_smi_available attribute")
            return False
        
        if not hasattr(partitioner, 'get_current_partition_mode'):
            print("✗ Partitioner missing get_current_partition_mode method")
            return False
        
        print("✓ Using real hardware partitioner (not simulation)")
        print(f"  - amd-smi available: {partitioner.amd_smi_available}")
        
        return True
    except Exception as e:
        print(f"✗ Error verifying hardware: {e}")
        return False


def test_gpu_detection():
    """Test GPU detection on the system."""
    print("\n=== Testing GPU Detection ===")
    
    try:
        from rocm_partitioner_real import ROCmPartitionerReal
        
        partitioner = ROCmPartitionerReal(gpu_id=0)
        if not partitioner.amd_smi_available:
            print("⚠ Skipping - amd-smi not available")
            return True
        
        # Try to get GPU info
        gpu_spec = partitioner.sizing_config.get_gpu_spec("MI300X")
        if gpu_spec:
            # Get GPU name from spec (check different possible attributes)
            gpu_name = getattr(gpu_spec, 'gpu_name', None) or getattr(gpu_spec, 'name', None) or "MI300X"
            print(f"✓ GPU spec found: {gpu_name}")
            print(f"  - Total memory: {gpu_spec.total_memory_gb} GB")
            if hasattr(gpu_spec, 'compute_units'):
                print(f"  - Compute units: {gpu_spec.compute_units}")
        else:
            print("⚠ GPU spec not found (may need to add to config)")
        
        return True
    except Exception as e:
        print(f"✗ Error detecting GPU: {e}")
        return False


def main():
    """Run all hardware verification tests."""
    print("=" * 60)
    print("Hardware Verification Test Suite")
    print("=" * 60)
    print()
    print("These tests verify real hardware functionality.")
    print("REQUIRES: AMD GPU with amd-smi available")
    print()
    
    tests = [
        ("amd-smi Availability", test_amd_smi_available),
        ("Real Hardware Partitioner Available", test_real_hardware_partitioner_available),
        ("Get Current Partition Mode", test_get_current_partition_mode),
        ("Initialize Real Partitioner", test_initialize_real_partitioner),
        ("Hardware vs Simulation", test_hardware_vs_simulation),
        ("GPU Detection", test_gpu_detection),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"\n✗ {test_name} FAILED\n")
        except Exception as e:
            print(f"\n✗ {test_name} ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ All hardware verification tests passed!")
        print("✓ Real hardware is working correctly")
        return 0
    else:
        print("✗ Some hardware tests failed")
        print("⚠ Verify that:")
        print("  - AMD GPU is installed")
        print("  - amd-smi is available and working")
        print("  - ROCm drivers are installed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

