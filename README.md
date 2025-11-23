# AIM.next (Q1 2026) Prototype Implementation

This repository contains the prototype implementation for three major AIM.next features:

1. **GPU Sharing/Partitioning** - ROCm-based multi-model deployment on single GPU
2. **AIM Guardrail Microservices** - Production-ready safety and filtering layers
3. **AIM Fine-Tuning Microservice** - Containerized fine-tuning with AIM profile integration

## Project Structure

```
AIM_Next/
├── aim-gpu-sharing/          # GPU sharing and partitioning prototype
├── aim-guardrails/           # Guardrail microservices prototype
├── aim-finetuning/           # Fine-tuning microservice prototype
├── docs/                     # Additional documentation
└── scripts/                   # Shared utility scripts
```

## Getting Started

### Prerequisites

- Kubernetes cluster with KServe installed
- ROCm 6.x installed on GPU nodes
- Docker/containerd for container runtime
- Python 3.10+
- Access to AMD Instinct GPUs (MI300X, MI350X, etc.)

### Development Setup

1. Clone this repository (or navigate to this directory)
2. Set up Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Review the [prototype recommendations document](./AIM_next_prototype_recommendations.md) for detailed architecture and implementation guidance

### Running Tests

Each component includes unit tests. Run tests to verify your setup:

```bash
# GPU Sharing tests
cd aim-gpu-sharing
python3 tests/run_tests.py  # Quick validation
pytest tests/ -v            # Full test suite

# See component-specific testing docs:
# - aim-gpu-sharing/TESTING.md
```

For comprehensive testing documentation, see component-specific testing guides.

## Feature Status

### GPU Sharing/Partitioning
- [x] Phase 1: Foundation (Weeks 1-2) - **✅ COMPLETE**
  - Real ROCm partitioner working on MI300X hardware
  - Model scheduler, resource isolator, hardware detector
  - 114 AIM profiles with partition mode information
  - 77 tests passing on real hardware
- [x] Phase 2: Integration (Weeks 3-4) - **✅ COMPLETE**
  - KServe CRD Extension with GPU sharing annotations
  - Kubernetes Partition Controller for automatic partition allocation
  - GPU Sharing Operator with RBAC and deployment manifests
- [x] Phase 3: QoS & Monitoring (Weeks 5-6) - **✅ COMPLETE**
  - Metrics Exporter (Prometheus) with partition and model metrics
  - QoS Framework with priority-based scheduling and SLO tracking
  - Grafana Dashboards for partition utilization, model performance, and scheduler metrics

### AIM Guardrails
- [ ] Phase 1: Core Guardrail Service (Weeks 1-3)
- [ ] Phase 2: Deployment Patterns (Weeks 4-5)
- [ ] Phase 3: Advanced Features (Weeks 6-8)

### AIM Fine-Tuning
- [ ] Phase 1: Core Fine-Tuning Service (Weeks 1-4)
- [ ] Phase 2: Job Management (Weeks 5-6)
- [ ] Phase 3: Advanced Features (Weeks 7-10)

## Contributing

See the prototype recommendations document for detailed implementation guidelines for each feature.

## License

MIT License (to be confirmed)


