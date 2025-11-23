# AIM Fine-Tuning Microservice

Containerized fine-tuning services compatible with AIM profiles, enabling model customization while maintaining deployment consistency.

## Features

- AIM-compatible fine-tuning containers
- Support for LoRA, QLoRA, and full fine-tuning
- Integration with AIM profile
- Automated profile generation for fine-tuned models
- KServe CRD for job management
- Checkpoint management and versioning

## Supported Fine-Tuning Methods

- **LoRA** (Low-Rank Adaptation) - Parameter-efficient fine-tuning
- **QLoRA** (Quantized LoRA) - Memory-efficient fine-tuning with quantization
- **Full Fine-Tuning** - Complete model fine-tuning

## Supported Model Architectures

- Llama (Meta)
- Mistral
- Qwen
- Gemma
- (More to be added)

## Architecture

See the main [prototype recommendations document](../AIM_next_prototype_recommendations.md#3-aim-fine-tuning-microservice-prototype) for detailed architecture.

## Directory Structure

```
aim-finetuning/
├── finetuning/          # Core fine-tuning components
│   ├── base/           # Base trainer
│   ├── methods/        # LoRA, QLoRA, full fine-tuning
│   ├── dataset/        # Dataset loading and preprocessing
│   └── profile/         # AIM profile generation
├── k8s/                # Kubernetes resources
├── checkpoint/         # Checkpoint management
├── monitoring/         # Metrics and dashboards
└── templates/          # Fine-tuning templates
```

## Development Status

🚧 In Development


