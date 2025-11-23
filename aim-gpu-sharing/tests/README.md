# Test Suite for AIM GPU Sharing

This directory contains unit tests for the GPU sharing and partitioning components.

**📖 For comprehensive testing documentation, see [../TESTING.md](../TESTING.md)**

## Quick Reference

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-asyncio
```

Or install all dependencies from the main requirements.txt:

```bash
pip install -r ../../requirements.txt
```

### Run All Tests

```bash
# From project root
cd aim-gpu-sharing
pytest

# Or with verbose output
pytest -v

# Or run specific test file
pytest tests/test_model_sizing.py -v
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests (when available)
pytest -m integration

# Run specific test class
pytest tests/test_model_sizing.py::TestModelSizingConfig -v

# Run specific test
pytest tests/test_model_sizing.py::TestModelSizingConfig::test_load_config -v
```

## Test Structure

### Unit Tests

- `test_model_sizing.py` - Tests for model sizing configuration and utilities
- `test_rocm_partitioner.py` - Tests for ROCm memory partitioner
- `test_model_scheduler.py` - Tests for model scheduler
- `test_resource_isolator.py` - Tests for resource isolator
- `test_aim_profile_generator.py` - Tests for AIM profile generation

### Integration Tests

Integration tests (requiring actual GPU hardware) should be placed in `tests/integration/`.

## Test Coverage

Current test coverage includes:

- ✅ Model sizing configuration loading and validation
- ✅ Model size estimation with different precision levels
- ✅ GPU specification retrieval
- ✅ Partition validation
- ✅ ROCm partitioner initialization and model allocation
- ✅ Model scheduler operations
- ✅ Resource isolator configuration
- ✅ AIM profile generation

## Writing New Tests

When adding new functionality, add corresponding tests:

1. Create test file: `test_<module_name>.py`
2. Import the module: `from <module> import <Class>`
3. Create test class: `class Test<Class>:`
4. Add test methods: `def test_<functionality>(self):`
5. Use fixtures from `conftest.py` when appropriate

### Example Test

```python
import pytest
from model_sizing import ModelSizingConfig

class TestNewFeature:
    def test_basic_functionality(self):
        config = ModelSizingConfig()
        result = config.new_method()
        assert result is not None
```

## Continuous Integration

Tests should be run in CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v
```

