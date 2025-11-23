#!/usr/bin/env python3
"""
Tests for KServe integration components.

Tests the partition controller logic and CRD schema without requiring
KServe to be installed in the cluster.
"""

import sys
import os
import yaml
from pathlib import Path

# Add paths
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))

controller_path = Path(__file__).parent.parent / "k8s" / "controller"
sys.path.insert(0, str(controller_path))

crd_path = Path(__file__).parent.parent / "k8s" / "crd"


def test_crd_schema_structure():
    """Test CRD schema structure."""
    print("\n=== Testing CRD Schema Structure ===")
    
    schema_file = crd_path / "schema.yaml"
    assert schema_file.exists(), "Schema file should exist"
    print("✓ Schema file exists")
    
    with open(schema_file, 'r') as f:
        schema = yaml.safe_load(f)
    
    # Check OpenAPI structure
    assert 'openapi' in schema, "Should be OpenAPI 3.0 schema"
    assert 'components' in schema, "Should have components section"
    assert 'schemas' in schema['components'], "Should have schemas"
    print("✓ OpenAPI schema structure correct")
    
    return True


def test_gpu_sharing_config_schema():
    """Test GPU sharing configuration schema."""
    print("\n=== Testing GPU Sharing Config Schema ===")
    
    schema_file = crd_path / "schema.yaml"
    with open(schema_file, 'r') as f:
        schema = yaml.safe_load(f)
    
    schemas = schema['components']['schemas']
    
    # Check GPUSharingConfig
    assert 'GPUSharingConfig' in schemas, "Should have GPUSharingConfig"
    gpu_config = schemas['GPUSharingConfig']
    
    assert 'properties' in gpu_config, "Should have properties"
    props = gpu_config['properties']
    
    # Check required properties
    required_props = ['enabled', 'partitionId', 'computeMode', 'memoryMode', 'qosPriority']
    for prop in required_props:
        if prop == 'enabled':
            assert prop in props or 'enabled' in gpu_config.get('required', []), f"Should have {prop}"
        else:
            assert prop in props, f"Should have {prop} property"
    
    print("✓ GPUSharingConfig schema has required properties")
    
    # Check enum values
    if 'computeMode' in props:
        assert 'enum' in props['computeMode'], "computeMode should have enum"
        assert 'SPX' in props['computeMode']['enum'], "Should support SPX mode"
        assert 'CPX' in props['computeMode']['enum'], "Should support CPX mode"
        print("✓ Compute mode enum values correct")
    
    if 'memoryMode' in props:
        assert 'enum' in props['memoryMode'], "memoryMode should have enum"
        assert 'NPS1' in props['memoryMode']['enum'], "Should support NPS1 mode"
        assert 'NPS4' in props['memoryMode']['enum'], "Should support NPS4 mode"
        print("✓ Memory mode enum values correct")
    
    if 'qosPriority' in props:
        assert 'enum' in props['qosPriority'], "qosPriority should have enum"
        assert 'low' in props['qosPriority']['enum'], "Should support low priority"
        assert 'medium' in props['qosPriority']['enum'], "Should support medium priority"
        assert 'high' in props['qosPriority']['enum'], "Should support high priority"
        print("✓ QoS priority enum values correct")
    
    return True


def test_partition_info_schema():
    """Test PartitionInfo schema."""
    print("\n=== Testing PartitionInfo Schema ===")
    
    schema_file = crd_path / "schema.yaml"
    with open(schema_file, 'r') as f:
        schema = yaml.safe_load(f)
    
    schemas = schema['components']['schemas']
    
    assert 'PartitionInfo' in schemas, "Should have PartitionInfo"
    partition_info = schemas['PartitionInfo']
    
    assert 'properties' in partition_info, "Should have properties"
    props = partition_info['properties']
    
    # Check required fields
    required_fields = ['partitionId', 'computeMode', 'memoryMode', 'partitionSizeGB']
    for field in required_fields:
        assert field in props, f"Should have {field} property"
    
    print("✓ PartitionInfo schema has required fields")
    
    return True


def test_controller_logic():
    """Test partition controller logic (without K8s dependency)."""
    print("\n=== Testing Partition Controller Logic ===")
    
    controller_file = controller_path / "partition_controller.py"
    assert controller_file.exists(), "Controller file should exist"
    print("✓ Controller file exists")
    
    with open(controller_file, 'r') as f:
        content = f.read()
    
    # Check for key classes and methods
    assert 'class PartitionController' in content, "Should have PartitionController class"
    print("✓ PartitionController class found")
    
    # Check for key methods
    required_methods = [
        '_get_gpu_sharing_config',
        '_should_manage',
        '_schedule_model',
        '_unschedule_model',
        '_update_status',
        'reconcile',
        'handle_delete',
        'run'
    ]
    
    for method in required_methods:
        assert f'def {method}' in content, f"Should have {method} method"
        print(f"✓ Method {method} found")
    
    # Check for GPU sharing config extraction
    assert 'gpuSharing' in content, "Should handle gpuSharing config"
    print("✓ GPU sharing config handling found")
    
    # Check for partition scheduling
    assert 'schedule_model' in content, "Should schedule models"
    print("✓ Model scheduling logic found")
    
    return True


def test_crd_yaml():
    """Test CRD YAML file structure."""
    print("\n=== Testing CRD YAML File ===")
    
    crd_file = crd_path / "gpu-sharing-crd.yaml"
    
    # CRD file might not exist, that's OK
    if not crd_file.exists():
        print("⚠ CRD YAML file not found (optional)")
        return True
    
    with open(crd_file, 'r') as f:
        crd = yaml.safe_load(f)
    
    # Check CRD structure
    assert 'apiVersion' in crd, "Should have apiVersion"
    assert 'kind' in crd, "Should have kind"
    assert crd['kind'] == 'CustomResourceDefinition', "Should be a CRD"
    print("✓ CRD YAML structure correct")
    
    if 'spec' in crd:
        spec = crd['spec']
        assert 'group' in spec, "Should have group"
        assert 'names' in spec, "Should have names"
        print("✓ CRD spec structure correct")
    
    return True


def test_operator_manifest():
    """Test operator manifest structure."""
    print("\n=== Testing Operator Manifest ===")
    
    operator_file = Path(__file__).parent.parent / "k8s" / "operator" / "gpu-sharing-operator.yaml"
    
    if not operator_file.exists():
        print("⚠ Operator manifest not found (optional)")
        return True
    
    with open(operator_file, 'r') as f:
        manifests = list(yaml.safe_load_all(f))
    
    assert len(manifests) > 0, "Should have at least one manifest"
    print(f"✓ Found {len(manifests)} manifest(s)")
    
    # Check for Deployment
    has_deployment = any(m.get('kind') == 'Deployment' for m in manifests)
    if has_deployment:
        print("✓ Deployment manifest found")
    
    return True


def test_rbac_manifest():
    """Test RBAC manifest structure."""
    print("\n=== Testing RBAC Manifest ===")
    
    rbac_file = Path(__file__).parent.parent / "k8s" / "operator" / "rbac.yaml"
    
    if not rbac_file.exists():
        print("⚠ RBAC manifest not found (optional)")
        return True
    
    with open(rbac_file, 'r') as f:
        manifests = list(yaml.safe_load_all(f))
    
    assert len(manifests) > 0, "Should have at least one manifest"
    print(f"✓ Found {len(manifests)} RBAC manifest(s)")
    
    # Check for ServiceAccount, Role, RoleBinding, or ClusterRole
    rbac_kinds = ['ServiceAccount', 'Role', 'RoleBinding', 'ClusterRole', 'ClusterRoleBinding']
    found_kinds = [m.get('kind') for m in manifests if m.get('kind') in rbac_kinds]
    
    if found_kinds:
        print(f"✓ Found RBAC resources: {', '.join(found_kinds)}")
    
    return True


def main():
    """Run all KServe integration tests."""
    print("=" * 60)
    print("KServe Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("CRD Schema Structure", test_crd_schema_structure),
        ("GPU Sharing Config Schema", test_gpu_sharing_config_schema),
        ("PartitionInfo Schema", test_partition_info_schema),
        ("Controller Logic", test_controller_logic),
        ("CRD YAML", test_crd_yaml),
        ("Operator Manifest", test_operator_manifest),
        ("RBAC Manifest", test_rbac_manifest),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"\n✗ {test_name} FAILED\n")
        except AssertionError as e:
            print(f"\n✗ {test_name} FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"\n✗ {test_name} ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

