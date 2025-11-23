#!/usr/bin/env python3
"""
Comprehensive test runner for KServe integration and QoS monitoring.

Runs all test suites and generates a summary report.
"""

import sys
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime

# Test modules
TEST_MODULES = [
    ('test_integration.py', 'Integration Tests (QoS + KServe)'),
    ('test_metrics_exporter.py', 'Metrics Exporter Tests'),
    ('test_kserve_integration.py', 'KServe Integration Tests'),
    ('test_qos_manager.py', 'QoS Manager Unit Tests'),
    ('test_kserve_e2e.py', 'KServe End-to-End Tests'),
    ('test_hardware_verification.py', 'Hardware Verification Tests'),
    ('test_rocm_partitioner.py', 'ROCm Partitioner Tests (Hardware)'),
]

def run_test_module(test_file, description):
    """Run a test module and return results."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"{'='*70}\n")
    
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        return {
            'name': description,
            'file': test_file,
            'status': 'SKIPPED',
            'reason': 'Test file not found',
            'duration': 0
        }
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        
        return {
            'name': description,
            'file': test_file,
            'status': 'PASSED' if result.returncode == 0 else 'FAILED',
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'duration': duration
        }
    except subprocess.TimeoutExpired:
        return {
            'name': description,
            'file': test_file,
            'status': 'TIMEOUT',
            'duration': 300
        }
    except Exception as e:
        return {
            'name': description,
            'file': test_file,
            'status': 'ERROR',
            'error': str(e),
            'duration': time.time() - start_time
        }


def check_prerequisites():
    """Check and install test prerequisites."""
    print("Checking test prerequisites...")
    
    missing = []
    
    # Check pytest
    try:
        import pytest
    except ImportError:
        missing.append("pytest")
    
    # Check prometheus_client
    try:
        import prometheus_client
    except ImportError:
        missing.append("prometheus-client")
    
    # Check yaml
    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")
    
    if missing:
        print(f"⚠ Missing prerequisites: {', '.join(missing)}")
        print("Installing prerequisites...")
        
        script_path = Path(__file__).parent / "install_prerequisites.sh"
        if script_path.exists():
            try:
                result = subprocess.run(
                    ['bash', str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    print("✓ Prerequisites installed successfully")
                else:
                    print(f"⚠ Prerequisites installation had issues: {result.stderr}")
            except Exception as e:
                print(f"⚠ Could not install prerequisites automatically: {e}")
                print("  Please run: bash tests/install_prerequisites.sh")
        else:
            print("  Please run: bash tests/install_prerequisites.sh")
    else:
        print("✓ All prerequisites are installed")
    
    print()


def check_kserve_installed():
    """Check if KServe is installed in the cluster."""
    import subprocess
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'crd', 'inferenceservices.serving.kserve.io'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def main():
    """Run all tests and generate report."""
    print("="*70)
    print("AIM GPU Sharing - Comprehensive Test Suite")
    print("Testing: KServe Integration & QoS Monitoring")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()
    
    # Check and install prerequisites
    check_prerequisites()
    
    # Check KServe installation
    kserve_installed = check_kserve_installed()
    if kserve_installed:
        print("✓ KServe is installed in the cluster")
    else:
        print("⚠ KServe is not installed - E2E tests will be skipped")
        print("  To install: cd tests && ./install_kserve.sh install")
    print()
    
    results = []
    
    for test_file, description in TEST_MODULES:
        # Skip E2E tests if KServe is not installed
        if 'End-to-End' in description and not kserve_installed:
            results.append({
                'name': description,
                'file': test_file,
                'status': 'SKIPPED',
                'reason': 'KServe not installed',
                'duration': 0
            })
            print(f"\n⊘ {description}: SKIPPED (KServe not installed)")
            continue
        
        result = run_test_module(test_file, description)
        results.append(result)
        
        # Print output
        if result.get('stdout'):
            print(result['stdout'])
        if result.get('stderr'):
            print(result['stderr'], file=sys.stderr)
        
        # Print status
        status_symbol = {
            'PASSED': '✓',
            'FAILED': '✗',
            'SKIPPED': '⊘',
            'TIMEOUT': '⏱',
            'ERROR': '⚠'
        }.get(result['status'], '?')
        
        print(f"\n{status_symbol} {result['name']}: {result['status']} ({result.get('duration', 0):.2f}s)")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    skipped = sum(1 for r in results if r['status'] == 'SKIPPED')
    errors = sum(1 for r in results if r['status'] in ['TIMEOUT', 'ERROR'])
    
    total_duration = sum(r.get('duration', 0) for r in results)
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ⊘ Skipped: {skipped}")
    print(f"  ⚠ Errors:  {errors}")
    print(f"\nTotal Duration: {total_duration:.2f}s")
    
    # Detailed results
    if failed > 0 or errors > 0:
        print("\n" + "="*70)
        print("FAILED/ERROR TESTS")
        print("="*70)
        for result in results:
            if result['status'] in ['FAILED', 'TIMEOUT', 'ERROR']:
                print(f"\n{result['name']} ({result['file']})")
                print(f"  Status: {result['status']}")
                if result.get('stderr'):
                    print(f"  Error: {result['stderr'][:200]}")
    
    print("\n" + "="*70)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Return code
    if failed > 0 or errors > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

