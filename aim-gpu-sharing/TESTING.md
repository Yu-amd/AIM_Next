# Testing Guide for AIM GPU Sharing

This document provides comprehensive instructions for running and writing tests for the GPU sharing and partitioning components.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)
- [Best Practices](#best-practices)

## Quick Start

### Prerequisites

#### 1. Kubernetes Cluster with AMD GPU Operator

Before running integration and end-to-end tests, you need a Kubernetes cluster with AMD GPU operator installed.

**Recommended Setup:** Use the [Kubernetes-MI300X repository](https://github.com/Yu-amd/Kubernetes-MI300X) for automated setup:

```bash
# Clone the setup repository
git clone https://github.com/Yu-amd/Kubernetes-MI300X.git
cd Kubernetes-MI300X

# Step 1: Install Kubernetes
sudo ./install-kubernetes.sh

# Step 2: Install AMD GPU Operator
./install-amd-gpu-operator.sh

# Verify installation
kubectl get pods -n kube-amd-gpu
```

**Alternative:** If you already have a Kubernetes cluster, install the AMD GPU operator manually following the [official documentation](https://github.com/RadeonOpenCompute/k8s-device-plugin).

#### 2. Python Dependencies

**Automatic Installation (Recommended):**

Test prerequisites are automatically installed when running tests. The test runner will check and install missing packages.

**Manual Installation:**

```bash
# From project root
pip install -r requirements.txt

# Or just testing dependencies
pip install pytest pytest-asyncio prometheus-client pyyaml kubernetes

# Or use the prerequisites script
cd aim-gpu-sharing/tests
./install_prerequisites.sh
```

#### 3. kubectl Configuration

Ensure `kubectl` is configured to access your cluster:

```bash
kubectl cluster-info
kubectl get nodes
```

### Run All Tests

#### Basic Tests (No Cluster Required)
```bash
# Quick validation (no pytest required)
cd aim-gpu-sharing
python3 tests/run_tests.py

# Integration tests (no KServe required)
python3 tests/run_all_tests.py
```

#### Full Test Suite (With KServe)
```bash
# Option 1: Use convenience script (recommended)
cd aim-gpu-sharing
./tests/run_tests_with_kserve.sh --install-kserve

# Option 2: Manual installation
cd aim-gpu-sharing/tests
./install_kserve.sh install
cd ..
python3 tests/run_all_tests.py
```

#### Full Test Suite with pytest
```bash
# Requires pytest installation
pytest tests/ -v
```

## Test Structure

```
aim-gpu-sharing/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures
│   ├── test_model_sizing.py         # Model sizing tests
│   ├── test_rocm_partitioner.py     # Partitioner tests
│   ├── test_model_scheduler.py      # Scheduler tests
│   ├── test_resource_isolator.py    # Isolator tests
│   ├── test_aim_profile_generator.py # Profile generator tests
│   ├── test_qos_manager.py          # QoS Manager unit tests
│   ├── test_integration.py          # Integration tests (QoS + KServe)
│   ├── test_metrics_exporter.py      # Metrics exporter tests
│   ├── test_kserve_integration.py    # KServe integration tests
│   ├── test_kserve_e2e.py            # KServe end-to-end tests
│   ├── run_tests.py                  # Quick test runner
│   ├── run_all_tests.py              # Comprehensive test runner
│   ├── run_tests_with_kserve.sh     # Convenience script with KServe
│   ├── install_kserve.sh            # KServe installation script
│   ├── README.md                     # Test infrastructure docs
│   ├── INSTALLATION_GUIDE.md         # KServe installation guide
│   ├── TEST_INFRASTRUCTURE.md        # Infrastructure documentation
│   └── TEST_SUMMARY.md               # Coverage summary
├── pytest.ini                        # Pytest configuration
└── runtime/                          # Source code being tested
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_model_sizing.py

# Run specific test class
pytest tests/test_model_sizing.py::TestModelSizingConfig

# Run specific test method
pytest tests/test_model_sizing.py::TestModelSizingConfig::test_load_config

# Run tests matching a pattern
pytest -k "partition"  # Runs all tests with "partition" in name
```

### Test Categories

```bash
# Run only unit tests (when markers are added)
pytest -m unit

# Run only integration tests (when available)
pytest -m integration

# Run slow tests separately
pytest -m slow
```

### Output Options

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Show coverage report (if pytest-cov installed)
pytest --cov=runtime --cov-report=html
```

### Quick Validation

For quick validation without pytest:

```bash
python3 tests/run_tests.py
```

This runs basic functionality tests and doesn't require pytest installation.

## New Test Scripts

### Prerequisites Installation Script (`tests/install_prerequisites.sh`)

Automated script to install Python dependencies required for tests:

```bash
cd tests
./install_prerequisites.sh
```

**Installs:**
- pytest and pytest-asyncio
- prometheus-client
- pyyaml
- kubernetes client (for E2E tests)

**Note:** The test runner (`run_all_tests.py`) automatically installs prerequisites if missing, so manual installation is optional.

### KServe Installation Script (`tests/install_kserve.sh`)

Automated script to install KServe in your Kubernetes cluster:

```bash
cd tests
./install_kserve.sh install    # Install KServe
./install_kserve.sh verify     # Verify installation
./install_kserve.sh uninstall  # Remove KServe
```

**Features:**
- Automatically installs cert-manager (if needed)
- Configurable via environment variables
- Verifies installation
- Handles errors gracefully
- Handles missing RBAC manifest files gracefully

See [tests/INSTALLATION_GUIDE.md](./tests/INSTALLATION_GUIDE.md) for detailed instructions.

### Comprehensive Test Runner (`tests/run_all_tests.py`)

Unified test runner that executes all test suites:

```bash
python3 tests/run_all_tests.py
```

**Features:**
- Automatically detects KServe installation
- Skips E2E tests if KServe not available
- Generates comprehensive reports
- Provides detailed failure information

### Convenience Script (`tests/run_tests_with_kserve.sh`)

Interactive script that optionally installs KServe before running tests:

```bash
./tests/run_tests_with_kserve.sh --install-kserve  # Force installation
./tests/run_tests_with_kserve.sh                   # Interactive prompt
./tests/run_tests_with_kserve.sh --skip-kserve     # Skip installation
```

### End-to-End Tests (`tests/test_kserve_e2e.py`)

Tests that require KServe to be installed:

```bash
# Ensure KServe is installed first
cd tests && ./install_kserve.sh install

# Run E2E tests
python3 tests/test_kserve_e2e.py
```

**Tests:**
- KServe installation verification
- InferenceService creation
- GPU sharing annotations
- CRD extension validation

For more details, see [tests/README.md](./tests/README.md).

## Writing Tests

### Test File Naming

- Test files must start with `test_`
- Example: `test_model_sizing.py`

### Test Class Naming

- Test classes must start with `Test`
- Example: `class TestModelSizingConfig:`

### Test Method Naming

- Test methods must start with `test_`
- Example: `def test_load_config(self):`

### Basic Test Template

```python
"""
Unit tests for <module_name>.
"""

import pytest
import sys
from pathlib import Path

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from <module> import <Class>


class Test<Class>:
    """Tests for <Class> class."""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return <Class>()
    
    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        result = instance.method()
        assert result is not None
    
    def test_edge_case(self, instance):
        """Test edge case."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

### Using Fixtures

Shared fixtures are in `conftest.py`:

```python
# Use shared fixtures
def test_with_fixture(sample_model_id, sample_gpu_name):
    """Test using shared fixtures."""
    assert sample_model_id == "meta-llama/Llama-3.1-8B-Instruct"
    assert sample_gpu_name == "MI300X"
```

### Testing Exceptions

```python
def test_raises_exception(self):
    """Test that exception is raised."""
    with pytest.raises(ValueError, match="error message"):
        function_that_raises()
```

### Testing with Mock Data

```python
def test_with_mock(self, monkeypatch):
    """Test with mocked dependency."""
    def mock_function():
        return "mocked"
    
    monkeypatch.setattr(module, "function", mock_function)
    result = code_under_test()
    assert result == "mocked"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("precision,expected_memory", [
    ("fp16", 20.0),
    ("int8", 13.0),
    ("int4", 9.0),
])
def test_precision_memory(self, precision, expected_memory):
    """Test memory for different precisions."""
    memory = estimate_memory(precision)
    assert memory == expected_memory
```

## Test Coverage

### Current Coverage

- ✅ Model sizing configuration (15 tests)
- ✅ ROCm partitioner (13 tests) - **Uses real hardware when available**
- ✅ Hardware verification (6 tests) - **Validates real hardware functionality**
- ✅ Model scheduler (13 tests)
- ✅ Resource isolator (11 tests)
- ✅ AIM profile generator (10 tests)
- ✅ QoS Manager (10 tests)
- ✅ KServe integration (7 tests)
- ✅ Metrics exporter (4 tests)
- ✅ KServe E2E (4 tests)

**Total: 93+ tests (61 unit + 32 integration/E2E)**

**Note:** The ROCm partitioner tests automatically detect and use real hardware (via `amd-smi`) when available, falling back to simulation mode only if hardware is not detected. The hardware verification tests explicitly verify that real hardware is being used. See [tests/HARDWARE_TESTING.md](./tests/HARDWARE_TESTING.md) for details.

### Coverage Goals

As we build out the project, aim for:

- **Unit tests**: 80%+ code coverage
- **Integration tests**: Critical paths covered
- **Edge cases**: All error paths tested
- **Documentation**: All public APIs have tests

### Generating Coverage Reports

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage
pytest --cov=runtime --cov-report=term-missing

# Generate HTML report
pytest --cov=runtime --cov-report=html
# Open htmlcov/index.html in browser
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd aim-gpu-sharing
          pytest tests/ -v
      
      - name: Generate coverage
        run: |
          pytest --cov=runtime --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['tests/', '-v']
```

## Best Practices

### 1. Test Organization

- **One test file per module**: `test_<module_name>.py`
- **One test class per class**: `Test<ClassName>`
- **One test method per behavior**: `test_<behavior>`

### 2. Test Naming

- Use descriptive names: `test_allocate_model_to_partition`
- Include what is being tested: `test_model_sizing_with_precision`
- Include expected outcome: `test_validation_fails_with_invalid_input`

### 3. Test Structure (AAA Pattern)

```python
def test_example(self):
    """Test description."""
    # Arrange - Set up test data
    model_id = "test/model"
    partition_id = 0
    
    # Act - Execute code under test
    result = scheduler.schedule_model(model_id, partition_id)
    
    # Assert - Verify results
    assert result is True
```

### 4. Test Independence

- Each test should be independent
- Don't rely on test execution order
- Clean up after tests (use fixtures)

### 5. Test Data

- Use realistic test data
- Test with actual model IDs from config
- Use fixtures for shared data

### 6. Assertions

- Use specific assertions: `assert result == expected`
- Include helpful messages: `assert result == expected, f"Got {result}, expected {expected}"`
- Test both positive and negative cases

### 7. Error Testing

- Test that errors are raised appropriately
- Test error messages are helpful
- Test error handling paths

### 8. Documentation

- Document complex test logic
- Explain why tests exist
- Update tests when behavior changes

## Adding Tests for New Features

When adding new functionality:

1. **Create test file**: `test_<new_module>.py`
2. **Add test class**: `class Test<NewClass>:`
3. **Write tests**: Cover all public methods
4. **Test edge cases**: Invalid inputs, boundary conditions
5. **Update this guide**: Document new patterns if needed

### Example: Adding Tests for New Module

```python
# tests/test_new_feature.py
"""
Unit tests for new feature module.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

from new_feature import NewClass


class TestNewClass:
    """Tests for NewClass."""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return NewClass()
    
    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        result = instance.method()
        assert result is not None
    
    def test_error_handling(self, instance):
        """Test error handling."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

## Troubleshooting

### Import Errors

If you see import errors:

```python
# Make sure runtime is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))

# Use try/except for relative imports
try:
    from .module import Class
except ImportError:
    from module import Class
```

### Test Discovery Issues

- Ensure test files start with `test_`
- Ensure test methods start with `test_`
- Check `pytest.ini` configuration

### Fixture Not Found

- Ensure fixture is in `conftest.py`
- Check fixture scope (function, class, module, session)
- Verify fixture name matches parameter name

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Testing Guide](https://docs.python.org/3/library/unittest.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

## Contributing

When contributing tests:

1. Follow the patterns in existing tests
2. Ensure all tests pass before submitting
3. Add tests for new features
4. Update this documentation if needed
5. Keep test coverage high

---

**Last Updated**: As we build out the project, this guide will be updated with new testing patterns and best practices.

