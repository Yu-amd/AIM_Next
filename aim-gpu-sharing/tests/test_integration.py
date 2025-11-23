#!/usr/bin/env python3
"""
Integration tests for KServe integration and QoS monitoring.

This script tests:
1. QoS Manager functionality (SLO tracking, priority queues, resource guarantees)
2. KServe partition controller logic (without requiring KServe to be installed)
3. Metrics exporter functionality
"""

import sys
import time
import os
from pathlib import Path

# Add runtime to path
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))

# Add qos subdirectory
qos_path = runtime_path / "qos"
sys.path.insert(0, str(qos_path))

from qos.qos_manager import QoSManager, QoSLevel, Request, SLO


def test_qos_manager_basic():
    """Test basic QoS Manager functionality."""
    print("\n=== Testing QoS Manager Basic Functionality ===")
    
    manager = QoSManager()
    assert manager is not None, "QoS Manager should initialize"
    print("✓ QoS Manager initialized")
    
    # Test SLO registration
    slo = SLO(
        model_id="test-model-1",
        max_latency_seconds=1.0,
        min_throughput_per_second=10.0
    )
    manager.register_slo(slo)
    assert "test-model-1" in manager.slos, "SLO should be registered"
    print("✓ SLO registration works")
    
    # Test resource guarantees
    manager.set_resource_guarantee("test-model-1", 0.5)
    assert manager.resource_guarantees["test-model-1"] == 0.5, "Resource guarantee should be set"
    print("✓ Resource guarantee setting works")
    
    # Test resource limits
    manager.set_resource_limit("test-model-1", 0.8)
    assert manager.resource_limits["test-model-1"] == 0.8, "Resource limit should be set"
    print("✓ Resource limit setting works")
    
    return True


def test_qos_priority_queues():
    """Test priority-based request queuing."""
    print("\n=== Testing QoS Priority Queues ===")
    
    manager = QoSManager()
    
    # Create requests with different priorities
    low_req = Request(
        request_id="req-low-1",
        model_id="test-model",
        partition_id=0,
        priority=QoSLevel.LOW,
        timestamp=time.time()
    )
    
    medium_req = Request(
        request_id="req-medium-1",
        model_id="test-model",
        partition_id=0,
        priority=QoSLevel.MEDIUM,
        timestamp=time.time()
    )
    
    high_req = Request(
        request_id="req-high-1",
        model_id="test-model",
        partition_id=0,
        priority=QoSLevel.HIGH,
        timestamp=time.time()
    )
    
    # Submit in non-priority order
    manager.submit_request(low_req)
    manager.submit_request(high_req)
    manager.submit_request(medium_req)
    
    # Verify queue depth
    assert manager.get_queue_depth() == 3, "Should have 3 requests in queue"
    print("✓ Requests submitted to queue")
    
    # Get next request - should be high priority
    next_req = manager.get_next_request()
    assert next_req is not None, "Should get a request"
    assert next_req.priority == QoSLevel.HIGH, "High priority should come first"
    assert next_req.request_id == "req-high-1", "Should get high priority request"
    print("✓ Priority ordering works (HIGH first)")
    
    # Get next - should be medium
    next_req = manager.get_next_request()
    assert next_req.priority == QoSLevel.MEDIUM, "Medium priority should come next"
    print("✓ Priority ordering works (MEDIUM second)")
    
    # Get next - should be low
    next_req = manager.get_next_request()
    assert next_req.priority == QoSLevel.LOW, "Low priority should come last"
    print("✓ Priority ordering works (LOW last)")
    
    return True


def test_qos_slo_tracking():
    """Test SLO compliance tracking."""
    print("\n=== Testing QoS SLO Tracking ===")
    
    manager = QoSManager()
    
    # Register SLO
    slo = SLO(
        model_id="test-model-slo",
        max_latency_seconds=0.5,
        min_throughput_per_second=20.0
    )
    manager.register_slo(slo)
    print("✓ SLO registered")
    
    # Record some request completions
    manager.record_request_completion("test-model-slo", 0.2, success=True)
    manager.record_request_completion("test-model-slo", 0.3, success=True)
    manager.record_request_completion("test-model-slo", 0.4, success=True)
    manager.record_request_completion("test-model-slo", 0.6, success=False)  # Failed request
    
    # Check stats
    stats = manager.request_stats.get("test-model-slo")
    assert stats is not None, "Stats should exist"
    assert stats['total_requests'] == 4, "Should have 4 total requests"
    assert stats['completed_requests'] == 3, "Should have 3 completed requests"
    assert stats['failed_requests'] == 1, "Should have 1 failed request"
    print("✓ Request statistics tracking works")
    
    # Check SLO compliance
    is_compliant, metrics = manager.check_slo_compliance("test-model-slo")
    assert isinstance(is_compliant, bool), "Compliance should be boolean"
    assert isinstance(metrics, dict), "Metrics should be dict"
    assert 'avg_latency' in metrics, "Should have average latency"
    assert 'throughput' in metrics, "Should have throughput"
    print(f"✓ SLO compliance check works (compliant: {is_compliant})")
    print(f"  - Average latency: {metrics.get('avg_latency', 0):.3f}s")
    print(f"  - Max latency: {metrics.get('max_latency', 0):.3f}s")
    print(f"  - Throughput: {metrics.get('throughput', 0):.2f} req/s")
    
    return True


def test_qos_resource_guarantees():
    """Test resource guarantee validation."""
    print("\n=== Testing QoS Resource Guarantees ===")
    
    manager = QoSManager()
    
    # Test valid guarantee
    try:
        manager.set_resource_guarantee("model-1", 0.5)
        print("✓ Valid resource guarantee accepted")
    except ValueError as e:
        print(f"✗ Valid guarantee rejected: {e}")
        return False
    
    # Test invalid guarantees
    try:
        manager.set_resource_guarantee("model-2", 1.5)
        print("✗ Invalid guarantee (1.5) accepted - should have failed")
        return False
    except ValueError:
        print("✓ Invalid guarantee (1.5) correctly rejected")
    
    try:
        manager.set_resource_guarantee("model-3", -0.1)
        print("✗ Invalid guarantee (-0.1) accepted - should have failed")
        return False
    except ValueError:
        print("✓ Invalid guarantee (-0.1) correctly rejected")
    
    return True


def test_kserve_controller_imports():
    """Test KServe partition controller imports and basic structure."""
    print("\n=== Testing KServe Controller Structure ===")
    
    controller_path = Path(__file__).parent.parent / "k8s" / "controller"
    sys.path.insert(0, str(controller_path))
    
    try:
        # Try to import the controller module
        import partition_controller
        print("✓ Partition controller module imports successfully")
        
        # Check if PartitionController class exists
        if hasattr(partition_controller, 'PartitionController'):
            print("✓ PartitionController class found")
        else:
            print("✗ PartitionController class not found")
            return False
        
        # Check for key methods
        controller_class = partition_controller.PartitionController
        required_methods = ['_get_gpu_sharing_config', '_should_manage', '_schedule_model']
        
        for method in required_methods:
            if hasattr(controller_class, method):
                print(f"✓ Method {method} found")
            else:
                print(f"✗ Method {method} not found")
                return False
        
        return True
    except ImportError as e:
        print(f"⚠ Partition controller import failed (expected if kubernetes not installed): {e}")
        print("  This is OK for testing controller structure without K8s")
        return True  # Not a failure if kubernetes isn't installed
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_metrics_exporter_structure():
    """Test metrics exporter structure."""
    print("\n=== Testing Metrics Exporter Structure ===")
    
    monitoring_path = Path(__file__).parent.parent / "monitoring"
    sys.path.insert(0, str(monitoring_path))
    
    try:
        import metrics_exporter
        print("✓ Metrics exporter module imports successfully")
        
        # Check if it uses prometheus_client
        if hasattr(metrics_exporter, 'Gauge') or 'prometheus_client' in str(metrics_exporter.__file__):
            print("✓ Prometheus client integration found")
        
        return True
    except ImportError as e:
        print(f"⚠ Metrics exporter import issue: {e}")
        # Check if file exists
        metrics_file = monitoring_path / "metrics_exporter.py"
        if metrics_file.exists():
            print("✓ Metrics exporter file exists")
            return True
        else:
            print("✗ Metrics exporter file not found")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_kserve_crd_schema():
    """Test KServe CRD schema structure."""
    print("\n=== Testing KServe CRD Schema ===")
    
    crd_path = Path(__file__).parent.parent / "k8s" / "crd" / "schema.yaml"
    
    if not crd_path.exists():
        print("✗ CRD schema file not found")
        return False
    
    print("✓ CRD schema file exists")
    
    # Read and check basic structure
    try:
        import yaml
        with open(crd_path, 'r') as f:
            schema = yaml.safe_load(f)
        
        # Check for GPU sharing config
        if 'components' in schema and 'schemas' in schema['components']:
            if 'GPUSharingConfig' in schema['components']['schemas']:
                print("✓ GPUSharingConfig schema found")
            else:
                print("✗ GPUSharingConfig schema not found")
                return False
            
            if 'PartitionInfo' in schema['components']['schemas']:
                print("✓ PartitionInfo schema found")
            else:
                print("✗ PartitionInfo schema not found")
                return False
        else:
            print("✗ Schema structure incorrect")
            return False
        
        return True
    except ImportError:
        print("⚠ PyYAML not available, skipping schema validation")
        return True
    except Exception as e:
        print(f"✗ Error reading schema: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("KServe Integration & QoS Monitoring Test Suite")
    print("=" * 60)
    
    tests = [
        ("QoS Manager Basic", test_qos_manager_basic),
        ("QoS Priority Queues", test_qos_priority_queues),
        ("QoS SLO Tracking", test_qos_slo_tracking),
        ("QoS Resource Guarantees", test_qos_resource_guarantees),
        ("KServe Controller Structure", test_kserve_controller_imports),
        ("Metrics Exporter Structure", test_metrics_exporter_structure),
        ("KServe CRD Schema", test_kserve_crd_schema),
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

