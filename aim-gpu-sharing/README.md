# AIM GPU Sharing/Partitioning

ROCm-based GPU resource sharing and partitioning to enable efficient multi-model deployment for smaller parameter models on a single GPU.

## Features

- ROCm-based GPU memory partitioning
- Multi-model concurrent serving on single GPU
- Resource isolation and QoS guarantees
- KServe CRD integration
- Prometheus metrics and monitoring

## Architecture

See the main [prototype recommendations document](../AIM_next_prototype_recommendations.md#1-gpu-sharingpartitioning-prototype) for detailed architecture.

## Directory Structure

```
aim-gpu-sharing/
├── runtime/              # Core runtime components
│   ├── rocm_partitioner.py
│   ├── model_scheduler.py
│   └── resource_isolator.py
├── k8s/                  # Kubernetes resources
│   ├── crd/              # Custom Resource Definitions
│   ├── controller/       # K8s controller
│   └── operator/         # K8s operator
├── monitoring/           # Metrics and dashboards
└── tests/                # Unit and integration tests
```

## Development Status

### Phase 1: Foundation ✅ COMPLETED
- ✅ ROCm memory partitioning layer
  - Simulation mode (`rocm_partitioner.py`) for development
  - **Real hardware mode** (`rocm_partitioner_real.py`) using actual MI300 partition modes
  - Based on [AMD MI300 partition modes guide](https://rocm.blogs.amd.com/software-tools-optimization/compute-memory-modes/)
- ✅ Model scheduler for multi-model deployment
- ✅ Resource isolator for compute isolation
- ✅ Model sizing with precision support (FP16, INT8, INT4)
- ✅ AIM profile generation (114 profiles)
- ✅ Comprehensive unit test suite (61 tests)

**⚠️ Important**: The original implementation was simulation-only. We now have `rocm_partitioner_real.py` that uses actual `amd-smi` commands and ROCm partition modes (CPX, NPS4) for real hardware. See [runtime/ROCM_PARTITIONING.md](./runtime/ROCM_PARTITIONING.md) for details.

### Phase 2: Integration 🚧 IN PROGRESS
- [ ] KServe CRD extension
- [ ] Kubernetes partition controller
- [ ] GPU sharing operator
- [ ] Metrics exporter

### Phase 3: QoS & Monitoring 📋 PLANNED
- [ ] QoS framework
- [ ] Grafana dashboards

**See [NEXT_STEPS.md](./NEXT_STEPS.md) for detailed implementation roadmap.**

## Testing

This project includes a comprehensive unit test suite. See [TESTING.md](./TESTING.md) for detailed testing instructions.

### Quick Start

```bash
# Run quick validation (no pytest required)
python3 tests/run_tests.py

# Run full test suite
pytest tests/ -v
```

### Test Coverage

- ✅ Model sizing configuration (15 tests)
- ✅ ROCm partitioner (12 tests)
- ✅ Model scheduler (13 tests)
- ✅ Resource isolator (11 tests)
- ✅ AIM profile generator (10 tests)

**Total: 61 unit tests** - All passing ✅

For detailed testing documentation, see [TESTING.md](./TESTING.md).


