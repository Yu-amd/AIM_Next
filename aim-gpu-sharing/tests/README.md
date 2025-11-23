# Test Infrastructure

This directory contains comprehensive test suites for KServe integration and QoS monitoring.

## Prerequisites

Before running tests, ensure you have:

1. **Kubernetes Cluster with AMD GPU Operator**
   - A running Kubernetes cluster (v1.20+) with AMD GPU operator installed
   - For setup instructions, see: [Kubernetes-MI300X Repository](https://github.com/Yu-amd/Kubernetes-MI300X)
   - Quick setup:
     ```bash
     # Clone the setup repository
     git clone https://github.com/Yu-amd/Kubernetes-MI300X.git
     cd Kubernetes-MI300X
     
     # Install Kubernetes
     sudo ./install-kubernetes.sh
     
     # Install AMD GPU Operator
     ./install-amd-gpu-operator.sh
     
     # Verify installation
     kubectl get pods -n kube-amd-gpu
     ```

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **kubectl** configured to access your cluster
   ```bash
   kubectl cluster-info
   ```

## Test Suites

### 1. Integration Tests (`test_integration.py`)
Tests QoS Manager and KServe integration components without requiring KServe to be installed.

**Run:**
```bash
python3 tests/test_integration.py
```

### 2. Metrics Exporter Tests (`test_metrics_exporter.py`)
Validates Prometheus metrics exporter structure and endpoints.

**Run:**
```bash
python3 tests/test_metrics_exporter.py
```

### 3. KServe Integration Tests (`test_kserve_integration.py`)
Tests KServe CRD schema, controller logic, and manifest structure.

**Run:**
```bash
python3 tests/test_kserve_integration.py
```

### 4. KServe End-to-End Tests (`test_kserve_e2e.py`)
**Requires KServe to be installed.** Tests actual InferenceService creation and GPU sharing integration.

**Run:**
```bash
python3 tests/test_kserve_e2e.py
```

### 5. QoS Manager Unit Tests (`test_qos_manager.py`)
Pytest-based unit tests for QoS Manager (requires pytest).

**Run:**
```bash
pytest tests/test_qos_manager.py -v
```

## Running All Tests

### Automatic Prerequisites Installation

The test runner automatically installs prerequisites if missing:
- pytest and pytest-asyncio
- prometheus-client
- pyyaml
- kubernetes client (for E2E tests)

You can also install prerequisites manually:
```bash
cd tests
./install_prerequisites.sh
```

### Quick Test (No KServe Required)
```bash
# From aim-gpu-sharing directory
python3 tests/run_all_tests.py
```

The test runner will:
1. Check and install prerequisites automatically
2. Detect KServe installation
3. Run all applicable tests
4. Generate comprehensive report

### Full Test Suite (With KServe)

**Option 1: Use Convenience Script (Recommended)**
```bash
# From aim-gpu-sharing directory
./tests/run_tests_with_kserve.sh --install-kserve
```

**Option 2: Manual Installation**
```bash
# Install KServe first
cd tests
./install_kserve.sh install

# Run all tests
cd ..
python3 tests/run_all_tests.py
```

**Option 3: Interactive Prompt**
```bash
# From aim-gpu-sharing directory
./tests/run_tests_with_kserve.sh
# Will prompt to install KServe if not detected
```

## KServe Installation

### Prerequisites
- Kubernetes cluster (v1.20+)
- kubectl configured to access the cluster
- Sufficient cluster resources

### Installation

```bash
cd tests
./install_kserve.sh install
```

### Verification

```bash
./install_kserve.sh verify
```

### Uninstallation

```bash
./install_kserve.sh uninstall
```

### Configuration

You can customize the installation by setting environment variables:

```bash
export KSERVE_VERSION=v0.12.0
export KSERVE_NAMESPACE=kserve
export CERT_MANAGER_VERSION=v1.13.0
./install_kserve.sh install
```

## Test Infrastructure Components

### Installation Script (`install_kserve.sh`)
- Installs cert-manager (if not present)
- Installs KServe
- Verifies installation
- Handles errors gracefully

### Test Runner (`run_all_tests.py`)
- Runs all test suites
- Generates comprehensive reports
- Skips E2E tests if KServe is not installed
- Provides detailed failure information

## Test Results

Test results are displayed in the console. For detailed reports, see `TEST_REPORT.md` in the parent directory.

## Troubleshooting

### KServe Installation Fails

1. Check cluster connectivity:
   ```bash
   kubectl cluster-info
   ```

2. Check cluster resources:
   ```bash
   kubectl top nodes
   ```

3. Check cert-manager:
   ```bash
   kubectl get pods -n cert-manager
   ```

### Tests Fail

1. **QoS Manager tests fail:**
   - These are unit tests and should work without any cluster setup
   - Check Python dependencies

2. **KServe E2E tests fail:**
   - Ensure KServe is installed: `./install_kserve.sh verify`
   - Check KServe controller: `kubectl get pods -n kserve`

3. **Import errors:**
   - Ensure you're running from the correct directory
   - Check that runtime modules are accessible

## Continuous Integration

For CI/CD pipelines, you can use:

```bash
# Install KServe
cd tests && ./install_kserve.sh install

# Run tests
cd .. && python3 tests/run_all_tests.py

# Exit code will be non-zero if tests fail
```

## Adding New Tests

1. Create test file: `test_<feature>.py`
2. Follow existing test patterns
3. Add to `TEST_MODULES` in `run_all_tests.py`
4. Update this README

## Test Coverage

- ✅ QoS Manager (priority queues, SLO tracking, resource management)
- ✅ Metrics Exporter (Prometheus integration, endpoints)
- ✅ KServe CRD Schema (OpenAPI validation)
- ✅ Partition Controller (logic and methods)
- ✅ KServe E2E (InferenceService creation, GPU sharing)
