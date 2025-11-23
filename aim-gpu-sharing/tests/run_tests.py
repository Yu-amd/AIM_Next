#!/usr/bin/env python3
"""
Simple test runner that validates basic functionality without pytest.

This can be used to quickly check if components work before running full pytest suite.
"""

import sys
from pathlib import Path

# Add runtime to path
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))


def test_model_sizing():
    """Test model sizing configuration."""
    print("Testing model sizing...")
    from model_sizing import ModelSizingConfig
    
    config = ModelSizingConfig()
    assert len(config.models) > 0, "No models loaded"
    
    model_info = config.get_model_size("meta-llama/Llama-3.1-8B-Instruct")
    assert model_info is not None, "Model not found"
    assert model_info.memory_gb > 0, "Invalid memory size"
    
    print("  ✓ Model sizing configuration loads correctly")
    print(f"  ✓ Found {len(config.models)} models")
    return True


def test_rocm_partitioner():
    """Test ROCm partitioner."""
    print("Testing ROCm partitioner...")
    from rocm_partitioner import ROCmPartitioner
    
    partitioner = ROCmPartitioner(gpu_id=0)
    success = partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
    assert success is True, "Partitioner initialization failed"
    
    model_id = "meta-llama/Llama-3.1-8B-Instruct"
    success, error = partitioner.allocate_model(model_id, partition_id=0)
    assert success is True, f"Model allocation failed: {error}"
    
    print("  ✓ Partitioner initialization works")
    print("  ✓ Model allocation works")
    return True


def test_model_scheduler():
    """Test model scheduler."""
    print("Testing model scheduler...")
    from model_scheduler import ModelScheduler
    from rocm_partitioner import ROCmPartitioner
    
    partitioner = ROCmPartitioner(gpu_id=0)
    partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])
    
    scheduler = ModelScheduler(partitioner)
    model_id = "meta-llama/Llama-3.1-8B-Instruct"
    
    success, partition_id, error = scheduler.schedule_model(model_id)
    assert success is True, f"Scheduling failed: {error}"
    assert partition_id is not None, "No partition assigned"
    
    print("  ✓ Model scheduling works")
    return True


def test_resource_isolator():
    """Test resource isolator."""
    print("Testing resource isolator...")
    from resource_isolator import ResourceIsolator
    
    isolator = ResourceIsolator(gpu_id=0)
    success = isolator.initialize(304, [0, 1, 2, 3])
    assert success is True, "Isolator initialization failed"
    
    env_vars = isolator.get_environment_variables(partition_id=0)
    assert "AIM_PARTITION_ID" in env_vars, "Missing environment variables"
    
    print("  ✓ Resource isolator works")
    return True


def test_aim_profile_generator():
    """Test AIM profile generator."""
    print("Testing AIM profile generator...")
    from aim_profile_generator import AIMProfileGenerator, PrecisionVariant
    
    generator = AIMProfileGenerator()
    model_id = "meta-llama/Llama-3.1-8B-Instruct"
    
    variants = [
        PrecisionVariant(precision="fp16", memory_gb=20.0, recommended_partition_gb=25.0)
    ]
    
    profiles = generator.generate_profiles_for_model(model_id, variants)
    assert len(profiles) > 0, "No profiles generated"
    assert profiles[0].model_id == model_id, "Wrong model ID in profile"
    
    print("  ✓ Profile generation works")
    return True


def main():
    """Run all basic tests."""
    print("Running basic functionality tests...\n")
    
    tests = [
        test_model_sizing,
        test_rocm_partitioner,
        test_model_scheduler,
        test_resource_isolator,
        test_aim_profile_generator,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"  ✗ Failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All basic tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

