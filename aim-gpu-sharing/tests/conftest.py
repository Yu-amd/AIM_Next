"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add runtime to path for imports
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))


@pytest.fixture(scope="session")
def test_config_path():
    """Path to test model sizing configuration."""
    return runtime_path / "model_sizing_config.yaml"


@pytest.fixture(scope="session")
def sample_model_id():
    """Sample model ID for testing."""
    return "meta-llama/Llama-3.1-8B-Instruct"


@pytest.fixture(scope="session")
def sample_gpu_name():
    """Sample GPU name for testing."""
    return "MI300X"

