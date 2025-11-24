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

See the [aim-gpu-sharing README](./aim-gpu-sharing/README.md) for detailed documentation, deployment guides, and validation instructions to test GPU sharing/partitioning on your own hardware.

### AIM Guardrails
- Core Guardrail Service - COMPLETE
  - Multiple guardrail types (toxicity, PII, prompt injection)
  - Policy management system
  - Configurable actions (block, warn, redact, modify)
- API & Integration - COMPLETE
  - REST API server for guardrail checking
  - Inference proxy for endpoint integration
  - Sidecar deployment pattern
- Kubernetes Integration - COMPLETE
  - GuardrailPolicy CRD
  - Deployment manifests
  - ConfigMap-based configuration

See the [aim-guardrails README](./aim-guardrails/README.md) for detailed documentation, usage examples, and deployment instructions.

### AIM Fine-Tuning
- Core Fine-Tuning Service - COMPLETE
  - LoRA, QLoRA, and Full fine-tuning implementations
  - Dataset loading and preprocessing (JSONL, CSV, HuggingFace)
  - AIM profile generation for fine-tuned models
  - Training orchestration and CLI
- Job Management - COMPLETE
  - KServe CRD for FineTuningJob
  - Kubernetes controller for job lifecycle
  - Checkpoint management with storage backends
  - Job status tracking and management
- Monitoring & Validation - COMPLETE
  - Prometheus metrics export (real-time training metrics, GPU utilization)
  - Validation framework (training loss, model output, checkpoint integrity)
  - SSH port forwarding support for remote monitoring
  - Automated validation reports

See the [aim-finetuning README](./aim-finetuning/README.md) for detailed documentation, usage examples, and testing instructions.

## License

MIT License
