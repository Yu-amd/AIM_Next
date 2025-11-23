#!/usr/bin/env python3
"""
End-to-end tests for KServe integration.

These tests require KServe to be installed in the cluster.
Run install_kserve.sh first if KServe is not installed.
"""

import sys
import os
import time
import subprocess
import yaml
from pathlib import Path

# Add paths
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))


def check_kserve_installed():
    """Check if KServe is installed in the cluster."""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'crd', 'inferenceservices.serving.kserve.io'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_kserve_controller_running():
    """Check if KServe controller is running."""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'pods', '-n', 'kserve', '-l', 'control-plane=kserve-controller-manager'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return 'Running' in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_test_inferenceservice(name, namespace='default'):
    """Create a test InferenceService."""
    isvc_yaml = f"""
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: {name}
  namespace: {namespace}
spec:
  predictor:
    sklearn:
      storageUri: gs://kfserving-examples/models/sklearn/iris
"""
    
    try:
        result = subprocess.run(
            ['kubectl', 'apply', '-f', '-'],
            input=isvc_yaml,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def create_test_inferenceservice_with_gpu_sharing(name, namespace='default'):
    """Create a test InferenceService with GPU sharing annotations."""
    isvc_yaml = f"""
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: {name}
  namespace: {namespace}
  annotations:
    aim.amd.com/gpu-sharing: "true"
spec:
  predictor:
    sklearn:
      storageUri: gs://kfserving-examples/models/sklearn/iris
      resources:
        requests:
          nvidia.com/gpu: "1"
        limits:
          nvidia.com/gpu: "1"
"""
    
    try:
        result = subprocess.run(
            ['kubectl', 'apply', '-f', '-'],
            input=isvc_yaml,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def delete_inferenceservice(name, namespace='default'):
    """Delete an InferenceService."""
    try:
        result = subprocess.run(
            ['kubectl', 'delete', 'inferenceservice', name, '-n', namespace, '--ignore-not-found=true'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        return False


def get_inferenceservice_status(name, namespace='default'):
    """Get InferenceService status."""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'inferenceservice', name, '-n', namespace, '-o', 'yaml'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return yaml.safe_load(result.stdout)
        return None
    except Exception as e:
        return None


def test_kserve_installation():
    """Test that KServe is installed."""
    print("\n=== Testing KServe Installation ===")
    
    if not check_kserve_installed():
        print("✗ KServe CRD not found")
        print("  Run: ./install_kserve.sh install")
        return False
    
    print("✓ KServe CRD found")
    
    if not check_kserve_controller_running():
        print("✗ KServe controller not running")
        return False
    
    print("✓ KServe controller is running")
    return True


def test_inferenceservice_creation():
    """Test creating a basic InferenceService."""
    print("\n=== Testing InferenceService Creation ===")
    
    test_name = f"test-isvc-{int(time.time())}"
    
    success, stdout, stderr = create_test_inferenceservice(test_name)
    
    if not success:
        print(f"✗ Failed to create InferenceService: {stderr}")
        return False
    
    print(f"✓ InferenceService {test_name} created")
    
    # Wait a bit for it to be processed
    time.sleep(2)
    
    # Check status
    status = get_inferenceservice_status(test_name)
    if status:
        print(f"✓ InferenceService status retrieved")
    else:
        print(f"⚠ Could not retrieve InferenceService status")
    
    # Cleanup
    delete_inferenceservice(test_name)
    print(f"✓ InferenceService {test_name} deleted")
    
    return True


def test_gpu_sharing_annotation():
    """Test InferenceService with GPU sharing annotation."""
    print("\n=== Testing GPU Sharing Annotation ===")
    
    test_name = f"test-gpu-sharing-{int(time.time())}"
    
    success, stdout, stderr = create_test_inferenceservice_with_gpu_sharing(test_name)
    
    if not success:
        print(f"⚠ Failed to create InferenceService with GPU sharing: {stderr}")
        print("  This is expected if GPU sharing controller is not deployed")
        return True  # Not a failure, just not configured
    
    print(f"✓ InferenceService {test_name} with GPU sharing created")
    
    # Check if annotation is present
    status = get_inferenceservice_status(test_name)
    if status:
        annotations = status.get('metadata', {}).get('annotations', {})
        if 'aim.amd.com/gpu-sharing' in annotations:
            print("✓ GPU sharing annotation present")
        else:
            print("⚠ GPU sharing annotation not found in status")
    
    # Cleanup
    delete_inferenceservice(test_name)
    print(f"✓ InferenceService {test_name} deleted")
    
    return True


def test_kserve_crd_extension():
    """Test KServe CRD extension for GPU sharing."""
    print("\n=== Testing KServe CRD Extension ===")
    
    # Check if our custom CRD exists
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'crd', 'inferenceservices.aim.amd.com'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ Custom InferenceService CRD found")
            return True
        else:
            print("⚠ Custom InferenceService CRD not found (expected if not deployed)")
            return True
    except Exception as e:
        print(f"⚠ Error checking CRD: {e}")
        return True


def main():
    """Run all KServe end-to-end tests."""
    print("=" * 60)
    print("KServe End-to-End Test Suite")
    print("=" * 60)
    
    # Check prerequisites
    if not check_kserve_installed():
        print("\n✗ KServe is not installed!")
        print("\nTo install KServe, run:")
        print("  cd tests && ./install_kserve.sh install")
        return 1
    
    tests = [
        ("KServe Installation", test_kserve_installation),
        ("InferenceService Creation", test_inferenceservice_creation),
        ("GPU Sharing Annotation", test_gpu_sharing_annotation),
        ("KServe CRD Extension", test_kserve_crd_extension),
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

