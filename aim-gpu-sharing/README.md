# AIM GPU Sharing/Partitioning

ROCm-based GPU resource sharing and partitioning to enable efficient multi-model deployment for smaller parameter models on a single GPU.

## Features

- ✅ **ROCm-based GPU memory partitioning** - Real hardware support with amd-smi
- ✅ **Multi-model concurrent serving** - Schedule multiple models on single GPU
- ✅ **Resource isolation** - Compute and memory isolation per partition
- ✅ **QoS guarantees** - Priority-based scheduling and SLO tracking
- ✅ **KServe CRD integration** - Kubernetes-native model serving
- ✅ **vLLM integration** - Deploy models using vLLM with GPU sharing (based on [AIM-Engine](https://github.com/Yu-amd/aim-engine))
- ✅ **Prometheus metrics** - Comprehensive monitoring and observability
- ✅ **Example applications** - CLI and web interfaces for model interaction

## Architecture

```
┌─────────────────────────────────────────────┐
│         KServe InferenceService            │
│      (with GPU sharing annotations)         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Partition Controller (K8s)              │
│  - Watches InferenceService resources       │
│  - Manages GPU partition allocation          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Model Scheduler                     │
│  - Multi-model scheduling                   │
│  - Resource allocation                      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      ROCm Partitioner (Real Hardware)       │
│  - SPX/CPX compute modes                    │
│  - NPS1/NPS4 memory modes                   │
│  - amd-smi integration                      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         AMD Instinct GPUs                    │
│      (MI300X, MI350X, etc.)                  │
└─────────────────────────────────────────────┘
```

See the main [prototype recommendations document](../AIM_next_prototype_recommendations.md#1-gpu-sharingpartitioning-prototype) for detailed architecture.

## Directory Structure

```
aim-gpu-sharing/
├── runtime/              # Core runtime components
│   ├── rocm_partitioner_real.py  # Real hardware partitioner
│   ├── rocm_partitioner.py       # Simulation partitioner
│   ├── model_scheduler.py        # Model scheduling
│   ├── resource_isolator.py      # Resource isolation
│   └── qos/                      # QoS management
│       └── qos_manager.py
├── k8s/                  # Kubernetes resources
│   ├── crd/              # Custom Resource Definitions
│   ├── controller/       # K8s controller
│   └── operator/         # K8s operator
├── monitoring/           # Metrics and dashboards
│   └── metrics_exporter.py
└── tests/                # Comprehensive test suite
    ├── test_hardware_verification.py
    ├── test_rocm_partitioner.py
    ├── test_integration.py
    └── test_kserve_e2e.py
```

## Development Status

### Phase 1: Foundation ✅ COMPLETED
- ✅ ROCm memory partitioning layer
  - **Real hardware mode** (`rocm_partitioner_real.py`) using actual MI300 partition modes
  - Simulation mode (`rocm_partitioner.py`) for development
  - Based on [AMD MI300 partition modes guide](https://rocm.blogs.amd.com/software-tools-optimization/compute-memory-modes/)
- ✅ Model scheduler for multi-model deployment
- ✅ Resource isolator for compute isolation
- ✅ Model sizing with precision support (FP16, INT8, INT4)
- ✅ AIM profile generation (114 profiles)
- ✅ Comprehensive unit test suite (93+ tests)

### Phase 2: Integration ✅ COMPLETED
- ✅ KServe CRD extension with GPU sharing annotations
- ✅ Kubernetes partition controller for automatic partition allocation
- ✅ GPU Sharing Operator with RBAC and deployment manifests
- ✅ Metrics exporter (Prometheus) with partition and model metrics

### Phase 3: QoS & Monitoring ✅ COMPLETED
- ✅ QoS Framework with priority-based scheduling and SLO tracking
- ✅ Prometheus metrics integration
- ✅ Grafana dashboards (partition utilization, model performance, scheduler metrics)

## Current Status

**✅ All core functionality implemented and tested**

- **Hardware Support**: Real hardware partitioner working with amd-smi
- **Test Coverage**: 93+ tests, all passing on real hardware
- **KServe Integration**: CRD schema, controller logic, and E2E tests validated
- **QoS System**: Priority queues, SLO tracking, resource guarantees working
- **Monitoring**: Metrics exporter structure validated

See [HARDWARE_TEST_STATUS.md](./HARDWARE_TEST_STATUS.md) for detailed hardware test results.

### Hardware Testing Notes

**⚠️ Important:** Digital Ocean MI300X instances do not advertise CPX (Compute Partition eXtended) mode support. As a result:
- **SPX mode testing**: Fully tested and validated (1 partition, 192GB)
- **CPX mode testing**: Limited testing due to hardware limitations
- **Multi-partition scenarios**: Some tests are skipped when only 1 partition is available
- **Multi-model concurrent tests**: Work correctly but may skip tests requiring 2+ partitions

For thorough CPX mode testing (8 partitions for MI300X), physical hardware or cloud providers that support CPX mode are required. The code supports CPX mode and will work correctly when hardware supports it.

## Quick Start

### Prerequisites

1. **Kubernetes Cluster with AMD GPU Operator**
   - A running Kubernetes cluster (v1.20+) with AMD GPU operator installed
   - For setup instructions, see: [Kubernetes-MI300X Repository](https://github.com/Yu-amd/Kubernetes-MI300X)
   - Quick setup:
     ```bash
     git clone https://github.com/Yu-amd/Kubernetes-MI300X.git
     cd Kubernetes-MI300X
     sudo ./install-kubernetes.sh
     ./install-amd-gpu-operator.sh
     ```

2. **Python Dependencies**
   - Test prerequisites are automatically installed when running tests
   - Or install manually: `cd tests && ./install_prerequisites.sh`

3. **kubectl** configured to access your cluster

### Running Tests

#### Automatic (Recommended)
```bash
# From aim-gpu-sharing directory
python3 tests/run_all_tests.py
```

The test runner automatically:
- Installs missing prerequisites
- Detects KServe installation
- Runs all applicable tests
- Generates comprehensive reports

#### Full Test Suite (With KServe)
```bash
# Option 1: Use convenience script (recommended)
./tests/run_tests_with_kserve.sh --install-kserve

# Option 2: Manual installation
cd tests
./install_kserve.sh install
cd ..
python3 tests/run_all_tests.py
```

### Test Suites

1. **Unit Tests** - Component-level tests (no cluster required)
   - Model sizing configuration (15 tests)
   - ROCm partitioner (13 tests) - **Uses real hardware when available**
   - Model scheduler (13 tests)
   - Resource isolator (11 tests)
   - AIM profile generator (10 tests)

2. **Hardware Verification Tests** - Real hardware validation
   - amd-smi availability and functionality
   - Real hardware partitioner initialization
   - Partition mode detection (SPX/CPX, NPS1/NPS4)
   - GPU detection and specifications
   - **Verifies tests are running on real hardware, not simulation**
   - **Note**: CPX mode testing is limited on Digital Ocean MI300X instances

3. **Integration Tests** - Component integration (no cluster required)
   - QoS Manager functionality
   - Metrics exporter structure
   - KServe CRD schema validation

4. **End-to-End Tests** - Full cluster testing (requires KServe)
   - KServe installation verification
   - InferenceService creation
   - GPU sharing annotations

**Total: 93+ tests** - All passing ✅

For detailed testing documentation, see [TESTING.md](./TESTING.md) and [tests/README.md](./tests/README.md).

## vLLM Integration

This project integrates with vLLM for actual model serving, following the workflow from [AIM-Engine](https://github.com/Yu-amd/aim-engine).

### Deployment Methods

We support two deployment methods:

1. **Docker Deployment** - Quick setup for development and testing
2. **Kubernetes Deployment** - Production-ready deployment with scaling and management

### Complete Deployment Guide

For step-by-step instructions on a clean node, see **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**.

This guide includes:
- Prerequisites and verification steps
- Docker deployment with validation
- Kubernetes deployment with validation
- Troubleshooting common issues
- Cleanup procedures

### Quick Start

#### Docker Deployment

```bash
# 1. Run vLLM container
docker run -d --name vllm-server \
  --device=/dev/kfd --device=/dev/dri \
  -p 8001:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000

# 2. Validate
curl http://localhost:8001/v1/models

# 3. Test web app
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

#### Kubernetes Deployment

```bash
# 1. Deploy model
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct

# 2. Validate
kubectl get pods -n aim-gpu-sharing
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
curl http://${NODE_IP}:30080/v1/models

# 3. Deploy web app
./k8s/deployment/deploy-web-app.sh
```

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete step-by-step instructions and validation procedures.

## Documentation

### Deployment Guides
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete step-by-step deployment guide (Docker & Kubernetes) with validation
- **[VLLM_INTEGRATION.md](./VLLM_INTEGRATION.md)** - vLLM integration details and architecture
- **[examples/README.md](./examples/README.md)** - Example applications and usage

### Testing Documentation
- **[TESTING.md](./TESTING.md)** - Comprehensive testing guide
- **[tests/README.md](./tests/README.md)** - Test infrastructure overview
- **[tests/HARDWARE_TESTING.md](./tests/HARDWARE_TESTING.md)** - Hardware testing documentation
- **[HARDWARE_TEST_STATUS.md](./HARDWARE_TEST_STATUS.md)** - Current hardware test status

### Reference
- **[DOCUMENTATION.md](./DOCUMENTATION.md)** - Complete documentation index
- **[STATUS.md](./STATUS.md)** - Project status and roadmap

## Contributing

See the prototype recommendations document for detailed implementation guidelines for each feature.

## License

MIT License (to be confirmed)
