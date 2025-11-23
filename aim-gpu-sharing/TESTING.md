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

Install test dependencies:

```bash
# From project root
pip install -r requirements.txt

# Or just testing dependencies
pip install pytest pytest-asyncio
```

### Run All Tests

```bash
# Quick validation (no pytest required)
cd aim-gpu-sharing
python3 tests/run_tests.py

# Full test suite with pytest
pytest tests/ -v
```

## Test Structure

```
aim-gpu-sharing/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_model_sizing.py     # Model sizing tests
│   ├── test_rocm_partitioner.py # Partitioner tests
│   ├── test_model_scheduler.py # Scheduler tests
│   ├── test_resource_isolator.py # Isolator tests
│   ├── test_aim_profile_generator.py # Profile generator tests
│   ├── run_tests.py             # Quick test runner
│   ├── README.md                # Test documentation
│   └── TEST_SUMMARY.md          # Coverage summary
├── pytest.ini                   # Pytest configuration
└── runtime/                     # Source code being tested
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
- ✅ ROCm partitioner (12 tests)
- ✅ Model scheduler (13 tests)
- ✅ Resource isolator (11 tests)
- ✅ AIM profile generator (10 tests)

**Total: 61 unit tests**

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

