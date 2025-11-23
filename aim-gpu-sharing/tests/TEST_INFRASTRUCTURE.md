# Test Infrastructure Overview

This document describes the comprehensive test infrastructure for KServe integration and QoS monitoring.

## Architecture

The test infrastructure consists of:

1. **Installation Scripts** - Automated KServe installation
2. **Unit Tests** - Component-level testing (no cluster required)
3. **Integration Tests** - Component integration testing
4. **End-to-End Tests** - Full cluster testing (requires KServe)
5. **Test Runner** - Unified test execution and reporting

## Components

### Installation Scripts

#### `install_kserve.sh`
Automated KServe installation script with:
- Prerequisite checking (kubectl, cluster connectivity)
- cert-manager installation (if needed)
- KServe installation and configuration
- Installation verification
- Uninstallation support

**Usage:**
```bash
./install_kserve.sh install    # Install KServe
./install_kserve.sh verify      # Verify installation
./install_kserve.sh uninstall   # Remove KServe
```

#### `run_tests_with_kserve.sh`
Convenience script that optionally installs KServe before running tests.

**Usage:**
```bash
./run_tests_with_kserve.sh                    # Interactive installation prompt
./run_tests_with_kserve.sh --install-kserve   # Force installation
./run_tests_with_kserve.sh --skip-kserve     # Skip installation
```

### Test Suites

#### 1. Integration Tests (`test_integration.py`)
**Status:** ✅ No cluster required

Tests:
- QoS Manager initialization and functionality
- Priority queue ordering (HIGH > MEDIUM > LOW)
- SLO tracking and compliance checking
- Resource guarantee/limit validation
- KServe controller structure
- Metrics exporter structure
- CRD schema validation

#### 2. Metrics Exporter Tests (`test_metrics_exporter.py`)
**Status:** ✅ No cluster required

Tests:
- Prometheus metrics structure
- HTTP endpoints (`/metrics`, `/health`)
- Metrics collection methods
- Metric definitions (11 metrics validated)

#### 3. KServe Integration Tests (`test_kserve_integration.py`)
**Status:** ✅ No cluster required

Tests:
- CRD schema structure (OpenAPI 3.0)
- GPU Sharing Config schema
- PartitionInfo schema
- Controller logic and methods
- Operator manifests
- RBAC configuration

#### 4. KServe End-to-End Tests (`test_kserve_e2e.py`)
**Status:** ⚠️ Requires KServe installation

Tests:
- KServe installation verification
- InferenceService creation
- GPU sharing annotations
- CRD extension validation

#### 5. QoS Manager Unit Tests (`test_qos_manager.py`)
**Status:** ⚠️ Requires pytest

Pytest-based unit tests for detailed QoS Manager testing.

### Test Runner

#### `run_all_tests.py`
Unified test runner that:
- Executes all test suites
- Detects KServe installation
- Skips E2E tests if KServe not available
- Generates comprehensive reports
- Provides detailed failure information

**Usage:**
```bash
python3 tests/run_all_tests.py
```

## Test Execution Flow

```
┌─────────────────────────────────────┐
│  run_all_tests.py                   │
│  or                                  │
│  run_tests_with_kserve.sh           │
└──────────────┬──────────────────────┘
               │
               ├─► Check KServe installed?
               │
       ┌───────┴────────┐
       │                │
   YES │                │ NO
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Run all      │  │ Skip E2E     │
│ tests        │  │ tests        │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                │
                ▼
        ┌───────────────┐
        │ Generate      │
        │ Report        │
        └───────────────┘
```

## Test Coverage

### QoS Monitoring
- ✅ Priority-based request queuing
- ✅ SLO tracking (latency, throughput)
- ✅ Resource guarantees and limits
- ✅ Request statistics
- ✅ Compliance checking

### Metrics Exporter
- ✅ Prometheus integration
- ✅ 11 metric definitions
- ✅ HTTP endpoints
- ✅ Collection methods

### KServe Integration
- ✅ CRD schema validation
- ✅ Controller logic
- ✅ GPU sharing configuration
- ✅ Partition information
- ✅ Operator manifests
- ✅ RBAC configuration

### End-to-End
- ✅ KServe installation
- ✅ InferenceService creation
- ✅ GPU sharing annotations
- ✅ CRD extension

## Running Tests

### Quick Test (No Setup)
```bash
cd aim-gpu-sharing
python3 tests/run_all_tests.py
```

### Full Test Suite
```bash
cd aim-gpu-sharing/tests
./install_kserve.sh install
cd ..
python3 tests/run_all_tests.py
```

### Convenience Script
```bash
cd aim-gpu-sharing
./tests/run_tests_with_kserve.sh --install-kserve
```

## Test Results

Test results are displayed in the console with:
- ✅ Passed tests
- ✗ Failed tests
- ⊘ Skipped tests
- ⚠ Errors

Detailed reports are available in `TEST_REPORT.md`.

## Continuous Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install KServe
  run: |
    cd aim-gpu-sharing/tests
    ./install_kserve.sh install

- name: Run Tests
  run: |
    cd aim-gpu-sharing
    python3 tests/run_all_tests.py
```

## Troubleshooting

### Common Issues

1. **KServe installation fails**
   - Check cluster connectivity: `kubectl cluster-info`
   - Check resources: `kubectl top nodes`
   - Check cert-manager: `kubectl get pods -n cert-manager`

2. **Tests fail with import errors**
   - Ensure you're in the correct directory
   - Check Python path includes runtime modules

3. **E2E tests skipped**
   - Install KServe: `./install_kserve.sh install`
   - Verify: `./install_kserve.sh verify`

## Adding New Tests

1. Create test file: `test_<feature>.py`
2. Follow existing patterns
3. Add to `TEST_MODULES` in `run_all_tests.py`
4. Update documentation

## Best Practices

1. **Run tests before committing:**
   ```bash
   python3 tests/run_all_tests.py
   ```

2. **Test locally before CI:**
   - Install KServe locally
   - Run full test suite

3. **Keep tests independent:**
   - Each test should be able to run standalone
   - Clean up resources after tests

4. **Document test requirements:**
   - Cluster requirements
   - Prerequisites
   - Expected behavior

## Future Enhancements

- [ ] Performance/load testing
- [ ] Chaos engineering tests
- [ ] Multi-GPU testing
- [ ] Network policy testing
- [ ] Security testing

