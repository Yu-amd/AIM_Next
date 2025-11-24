# AIM Fine-Tuning Microservice

Containerized fine-tuning services compatible with AIM profiles, enabling model customization while maintaining deployment consistency.

## Overview

The AIM Fine-Tuning Microservice provides a complete solution for fine-tuning large language models with support for multiple methods, Kubernetes integration, monitoring, and validation. It automatically generates AIM profiles for fine-tuned models, ensuring seamless integration with the AIM deployment ecosystem.

## Features

- **Multiple Fine-Tuning Methods**: LoRA, QLoRA, and Full fine-tuning
- **AIM Profile Integration**: Automatic profile generation for fine-tuned models
- **Kubernetes Native**: KServe CRD and controller for job management
- **Monitoring & Metrics**: Prometheus metrics export with real-time training metrics
- **Validation Framework**: Automated quality checks and validation reports
- **Checkpoint Management**: Save, load, version, and resume training
- **Multiple Dataset Formats**: JSONL, CSV, and HuggingFace datasets

## Supported Fine-Tuning Methods

- **LoRA** (Low-Rank Adaptation) - Parameter-efficient fine-tuning with minimal memory overhead
- **QLoRA** (Quantized LoRA) - Memory-efficient fine-tuning with 4-bit quantization
- **Full Fine-Tuning** - Complete model fine-tuning with all parameters trainable

## Supported Model Architectures

- Llama (Meta)
- Mistral
- Qwen
- Gemma
- (More architectures supported via HuggingFace transformers)

## Quick Start

### Prerequisites

- Python 3.10+
- PyTorch with ROCm support (for AMD GPUs) 
- GPU with sufficient memory (16GB+ recommended for 7B models)
- HuggingFace account (for gated models)

### Installation

```bash
cd aim-finetuning
pip install -r requirements.txt --break-system-packages
```

### Basic Usage

#### LoRA Fine-Tuning

```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method lora \
  --learning-rate 2e-4 \
  --batch-size 4 \
  --epochs 3 \
  --lora-rank 16 \
  --lora-alpha 32
```

#### QLoRA Fine-Tuning (Memory-Efficient)

```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method qlora \
  --learning-rate 2e-4 \
  --batch-size 4 \
  --epochs 3 \
  --lora-rank 16 \
  --lora-alpha 32 \
  --fp16
```

#### Full Fine-Tuning

```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method full \
  --learning-rate 2e-5 \
  --batch-size 2 \
  --epochs 3 \
  --gradient-checkpointing \
  --fp16
```

#### With Monitoring Enabled

```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method lora \
  --enable-metrics \
  --metrics-port 8000
```

Then access metrics at `http://localhost:8000/metrics` or via SSH port forwarding.

## Dataset Format

The fine-tuning service supports multiple dataset formats:

### JSONL Format (Conversation)

```jsonl
{"instruction": "What is AI?", "output": "AI is artificial intelligence."}
{"instruction": "Explain ML.", "output": "ML is machine learning."}
{"instruction": "What is deep learning?", "input": "Context about neural networks", "output": "Deep learning is a subset of ML..."}
```

### CSV Format

```csv
instruction,output
"What is AI?","AI is artificial intelligence."
"Explain ML.","ML is machine learning."
```

### HuggingFace Datasets

```bash
# Use HuggingFace dataset ID
--dataset-path "dataset_name" --dataset-format hf
```

## Development Status

### ✅ Phase 1: Core Fine-Tuning Service - COMPLETE

- [x] Base trainer infrastructure
- [x] LoRA trainer implementation
- [x] QLoRA trainer implementation (4-bit quantization)
- [x] Full fine-tuning trainer
- [x] Dataset loading and preprocessing (JSONL, CSV, HuggingFace)
- [x] Training orchestration and CLI
- [x] AIM profile integration and generation

### ✅ Phase 2: Job Management - COMPLETE

- [x] KServe CRD for FineTuningJob
- [x] Kubernetes controller for job lifecycle
- [x] Job status tracking and management
- [x] Checkpoint management (save, load, version, resume)
- [x] Storage backends (local filesystem, S3-compatible)

### ✅ Phase 3: Monitoring & Validation - COMPLETE

- [x] Prometheus metrics export
  - Real-time training metrics (loss, learning rate, throughput)
  - GPU utilization and memory tracking
  - Checkpoint metrics
  - Job status tracking
- [x] Validation framework
  - Training loss validation
  - Model output validation
  - Checkpoint integrity checks
  - AIM profile validation
  - Automated validation reports
- [x] Remote monitoring support (SSH port forwarding)
- [x] Standalone metrics server

## Architecture

```
aim-finetuning/
├── finetuning/          # Core fine-tuning components
│   ├── base/           # Base trainer and CLI
│   ├── methods/        # LoRA, QLoRA, full fine-tuning
│   ├── dataset/        # Dataset loading and preprocessing
│   └── profile/        # AIM profile generation
├── monitoring/          # Monitoring and validation
│   ├── metrics.py      # Prometheus metrics exporter
│   ├── metrics_server.py  # Standalone metrics server
│   ├── validate_job.py # Validation CLI tool
│   └── validators/     # Validation framework
├── k8s/                # Kubernetes resources
│   ├── crd/            # FineTuningJob CRD
│   └── controller/     # Kubernetes controller
├── checkpoint/         # Checkpoint management
└── templates/          # Example datasets and configs
```

## Monitoring & Metrics

### Prometheus Metrics

The service exposes comprehensive Prometheus metrics:

- **Job Status**: `finetuning_job_status`, `finetuning_job_duration_seconds`
- **Training Progress**: `finetuning_training_epoch`, `finetuning_training_step`, `finetuning_training_progress`
- **Performance**: `finetuning_train_loss`, `finetuning_learning_rate`, `finetuning_samples_per_second`
- **Resources**: `finetuning_gpu_utilization_percent`, `finetuning_gpu_memory_used_bytes`
- **Checkpoints**: `finetuning_checkpoints_total`, `finetuning_checkpoint_size_bytes`

### Remote Monitoring

Access metrics remotely via SSH port forwarding:

```bash
# On local machine
ssh -L 8000:localhost:8000 user@remote-server

# Then access metrics
curl http://localhost:8000/metrics | grep finetuning
```

See [MONITORING.md](./MONITORING.md) for detailed monitoring documentation.

## Validation

### Automated Validation

Validate training results after completion:

```bash
python3 -m monitoring.validate_job \
  --training-info ./output/training_info.json \
  --model-path ./output \
  --profile-path ./output/aim_profile.json
```

### Validation Checks

- Training loss validation (range checks)
- Model output validation (generation testing)
- Checkpoint integrity verification
- AIM profile format validation

## Testing

### Quick Automated Tests

```bash
# Test LoRA fine-tuning
./test_lora.sh

# Test QLoRA fine-tuning
./test_qlora.sh

# Test Full fine-tuning
./test_full.sh

# Test monitoring and validation
./test_monitoring.sh
```

### Manual Testing

See [TESTING.md](./TESTING.md) for comprehensive testing instructions, including:
- Prerequisites and setup
- Manual testing procedures
- Troubleshooting guide
- Performance benchmarks

## Kubernetes Deployment

### Deploy FineTuningJob CRD

```bash
kubectl apply -f k8s/crd/finetuning-job-crd.yaml
```

### Create FineTuningJob

```yaml
apiVersion: aim.amd.com/v1alpha1
kind: FineTuningJob
metadata:
  name: qwen-lora-finetune
  namespace: aim-finetuning
spec:
  baseModel:
    modelId: "Qwen/Qwen2.5-7B-Instruct"
  method: lora
  dataset:
    source: "configmap:finetuning-templates:example_dataset.jsonl"
    format: jsonl
  hyperparameters:
    learningRate: 0.0002
    batchSize: 4
    epochs: 3
    loraRank: 16
    loraAlpha: 32
  output:
    registry: "your-registry/finetuned-models"
  resources:
    limits:
      amd.com/gpu: "1"
    requests:
      amd.com/gpu: "1"
```

### Controller

The Kubernetes controller watches for FineTuningJob resources and manages training pods. See `k8s/controller/` for implementation details.

## AIM Profile Integration

The service automatically generates AIM profiles for fine-tuned models:

- Estimates memory requirements based on method and precision
- Calculates recommended GPU partition sizes
- Includes training metadata and configuration
- Saves profile as `aim_profile.json` in output directory

Example profile:

```json
{
  "model_id": "Qwen/Qwen2.5-7B-Instruct-finetuned",
  "base_model_id": "Qwen/Qwen2.5-7B-Instruct",
  "fine_tuning_method": "lora",
  "precision": "fp16",
  "memory_gb": 15.0,
  "recommended_partition_gb": 18.75,
  "parameters": "7B"
}
```

## Checkpoint Management

The service supports checkpoint management:

- Automatic checkpoint saving during training
- Checkpoint versioning
- Resume training from checkpoints
- Storage backends (local filesystem, S3-compatible)

## Documentation

- [TESTING.md](./TESTING.md) - Comprehensive testing guide
- [MONITORING.md](./MONITORING.md) - Monitoring and metrics documentation
- [k8s/README.md](./k8s/README.md) - Kubernetes deployment guide (if available)

## Examples

See `templates/` directory for:
- Example dataset (`example_dataset.jsonl`)
- Example configuration files
- Training templates

## Performance Benchmarks

Typical training times on MI300X (192GB):

- **Qwen2.5-7B-Instruct** with LoRA (rank=16):
  - Small dataset (100 examples): ~5-10 minutes
  - Medium dataset (1000 examples): ~30-60 minutes
  - Large dataset (10000 examples): ~5-10 hours

Note: Times vary based on sequence length, batch size, and other hyperparameters.

## Troubleshooting

### Common Issues

- **`ModuleNotFoundError`**: Install dependencies from `requirements.txt`
- **`GPU out of memory`**: Reduce batch size or use QLoRA method
- **`Metrics server port in use`**: Use `--metrics-port` to specify different port
- **`Dataset format error`**: Ensure dataset matches expected format (see Dataset Format section)

See [TESTING.md](./TESTING.md) for detailed troubleshooting guide.

## Contributing

This is a prototype implementation. For production use, consider:
- Adding more validation checks
- Implementing hyperparameter optimization
- Adding support for more model architectures
- Enhancing checkpoint management features

## License

MIT License
