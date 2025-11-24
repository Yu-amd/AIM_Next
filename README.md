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
- ROCm 7.* installed on GPU nodes
- Docker/containerd for container runtime
- Python 3.10+
- Access to AMD Instinct GPUs (MI300X, MI325X, etc.)

### Development Setup

1. Clone this repository (or navigate to this directory)
2. Set up Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Feature Status

### GPU Sharing/Partitioning
- Foundation - COMPLETE
  - Real ROCm partitioner working on MI300X hardware
  - Model scheduler, resource isolator, hardware detector
  - 114 AIM profiles with partition mode information
  - 77 tests passing on real hardware
- Integration - COMPLETE
  - KServe CRD Extension with GPU sharing annotations
  - Kubernetes Partition Controller for automatic partition allocation
  - GPU Sharing Operator with RBAC and deployment manifests
- QoS & Monitoring - COMPLETE
  - Metrics Exporter (Prometheus) with partition and model metrics
  - QoS Framework with priority-based scheduling and SLO tracking
  - Grafana Dashboards for partition utilization, model performance, and scheduler metrics

**Try it out:** See the [aim-gpu-sharing README](./aim-gpu-sharing/README.md) for detailed documentation, deployment guides, and validation instructions to test GPU sharing/partitioning on your own hardware.

### AIM Guardrails
- Core Guardrail Service
- Deployment Patterns
- Advanced Features

### AIM Fine-Tuning
- Core Fine-Tuning Service (Weeks 1-4)
- Job Management (Weeks 5-6)
- Advanced Features (Weeks 7-10)

## License

MIT License
