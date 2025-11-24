# AIM.next (Q1 2026) Prototype Recommendations

## Executive Summary

This document provides technical recommendations for prototyping three major features for AIM.next:
1. **GPU Sharing/Partitioning** - ROCm-based multi-model deployment on single GPU
2. **AIM Guardrail Microservices** - Production-ready safety and filtering layers
3. **AIM Fine-Tuning Microservice** - Containerized fine-tuning with AIM profile integration

## 1. GPU Sharing/Partitioning Prototype

### 1.1 Architecture Overview

**Objective**: Enable 2-8 smaller models (<70B parameters) to run concurrently on a single MI300X/MI350X GPU with proper isolation and QoS guarantees.

### 1.2 Technical Approach

#### Phase 1: Foundation (Weeks 1-2)
- **ROCm Memory Partitioning Layer**
  - Implement a Python/C++ wrapper around ROCm APIs for memory partitioning
  - Create a memory allocator that can divide GPU memory into isolated regions
  - Use `hipMalloc` with memory pools per partition
  - Reference: AMD GPU Partitioning documentation for MI300X

- **Basic Multi-Model Runtime**
  - Extend vLLM to support multiple model instances with memory constraints
  - Implement a model scheduler that manages multiple vLLM instances
  - Each instance gets a dedicated memory partition via environment variables

#### Phase 2: Integration (Weeks 3-4)
- **KServe CRD Extension**
  - Extend existing AIM InferenceService CRD with GPU sharing annotations:
    ```yaml
    annotations:
      aim.amd.com/gpu-sharing: "enabled"
      aim.amd.com/memory-limit: "40GB"
      aim.amd.com/partition-id: "0"
    ```
  - Create a GPU partition scheduler that validates resource requests

- **Resource Isolation**
  - Implement compute isolation using ROCm's MIG-like capabilities
  - Use `ROCR_VISIBLE_DEVICES` and memory limits per container
  - Docker/containerd integration for GPU device isolation

#### Phase 3: QoS & Monitoring (Weeks 5-6)
- **QoS Framework**
  - Priority-based scheduling for model requests
  - Minimum/maximum resource guarantees per partition
  - Latency SLO tracking per model

- **Metrics & Monitoring**
  - Prometheus exporters for per-partition metrics:
    - GPU memory usage per partition
    - Compute utilization per partition
    - Request latency per model
    - Throughput per model
  - Grafana dashboards for visualization

### 1.3 Prototype Structure

```
aim-gpu-sharing/
├── runtime/
│   ├── rocm_partitioner.py      # ROCm memory partitioning wrapper
│   ├── model_scheduler.py       # Multi-model scheduler
│   └── resource_isolator.py     # Compute isolation logic
├── k8s/
│   ├── crd/
│   │   └── gpu-sharing-crd.yaml # Extended InferenceService CRD
│   ├── controller/
│   │   └── partition_controller.py # K8s controller for partitions
│   └── operator/
│       └── gpu-sharing-operator.yaml
├── monitoring/
│   ├── metrics_exporter.py      # Prometheus metrics
│   └── dashboards/              # Grafana dashboards
└── tests/
    ├── unit/                    # Unit tests
    └── integration/             # Integration tests with real GPU
```

### 1.4 Key Technical Decisions

1. **Memory Partitioning Strategy**
   - Use ROCm's memory pool allocation
   - Static partitioning initially (fixed partitions at startup)
   - Dynamic partitioning as Phase 2 enhancement

2. **Model Compatibility**
   - Focus on models <70B parameters initially
   - Support vLLM backend first (P0)
   - SGLang backend as Phase 2 (P1)

3. **Validation**
   - Pre-deployment validation: Check model size vs. partition size
   - Runtime validation: Monitor memory usage and trigger alerts

### 1.5 Success Criteria

- [ ] Deploy 2-4 models concurrently on MI300X (192GB)
- [ ] Each model maintains <10% latency degradation vs. dedicated GPU
- [ ] Memory isolation prevents cross-partition interference
- [ ] QoS guarantees met for priority models
- [ ] Metrics exposed via Prometheus

---

## 2. AIM Guardrail Microservices Prototype

### 2.1 Architecture Overview

**Objective**: Deploy lightweight guardrail models (<3B parameters) as sidecar containers with <50ms latency overhead for real-time content filtering.

### 2.2 Technical Approach

#### Phase 1: Core Guardrail Service (Weeks 1-3)
- **Guardrail Microservice Container**
  - AIM-compatible container following AIM Build patterns
  - FastAPI-based HTTP service with `/filter` endpoint
  - Support for input filtering (pre-inference) and output filtering (post-inference)
  - Async processing for low latency

- **Initial Guardrail Models** (P0)
  - **Toxicity Detection**: Deploy small model (<1B) like `unitary/toxic-bert`
  - **NSFW Filter**: Deploy `Falconsai/nsfw_image_detection` or similar
  - **PII Detection**: Use regex + lightweight NER model (1-3B)
  - **Prompt Injection**: Deploy specialized model like `protectai/deberta-v3-base-prompt-injection-v2`

- **AIM Profile Format for Guardrails**
  ```json
  {
    "model_id": "unitary/toxic-bert",
    "guardrail_type": "toxicity",
    "latency_target_ms": 50,
    "resource_requirements": {
      "gpu_memory_gb": 2,
      "cpu_cores": 1
    },
    "thresholds": {
      "toxicity_score": 0.3
    }
  }
  ```

#### Phase 2: Deployment Patterns (Weeks 4-5)
- **Sidecar Pattern**
  - Kubernetes sidecar container in same pod as AIM inference
  - Shared volume for communication or HTTP/gRPC
  - Istio service mesh integration for automatic sidecar injection

- **Proxy Pattern**
  - Envoy-based proxy that intercepts requests
  - Routes through guardrail before/after AIM inference
  - Configurable routing rules

- **KServe Integration**
  - Extend InferenceService CRD with guardrail annotations:
    ```yaml
    annotations:
      aim.amd.com/guardrails: |
        - type: toxicity
          threshold: 0.3
        - type: pii
          action: redact
    ```

#### Phase 3: Advanced Features (Weeks 6-8)
- **Multi-Guardrail Orchestration**
  - Pipeline configuration for multiple guardrails
  - Sequential or parallel execution
  - Early termination on first failure

- **Configurable Policies**
  - YAML/JSON policy configuration
  - Per-endpoint or per-tenant policies
  - Dynamic policy updates via ConfigMap

- **Monitoring & Observability**
  - Metrics: Latency, filtering rate, false positive/negative rates
  - Logging: Filtered content (with privacy controls)
  - Tracing: Distributed tracing for guardrail pipeline

### 2.3 Prototype Structure

```
aim-guardrails/
├── guardrails/
│   ├── base/
│   │   ├── Dockerfile           # Base guardrail container
│   │   ├── app.py              # FastAPI application
│   │   └── guardrail_base.py   # Base guardrail class
│   ├── toxicity/
│   │   ├── Dockerfile
│   │   └── toxicity_detector.py
│   ├── pii/
│   │   ├── Dockerfile
│   │   └── pii_detector.py
│   ├── prompt_injection/
│   │   ├── Dockerfile
│   │   └── injection_detector.py
│   └── nsfw/
│       ├── Dockerfile
│       └── nsfw_detector.py
├── orchestrator/
│   ├── pipeline.py             # Multi-guardrail pipeline
│   └── policy_engine.py         # Policy configuration engine
├── k8s/
│   ├── crd/
│   │   └── guardrail-crd.yaml
│   ├── sidecar/
│   │   └── sidecar-injector.yaml
│   └── proxy/
│       └── envoy-config.yaml
├── profiles/
│   └── guardrail-profiles/      # AIM profiles for guardrails
└── monitoring/
    ├── metrics.py
    └── dashboards/
```

### 2.4 Key Technical Decisions

1. **Model Selection**
   - Prioritize models <3B parameters for low latency
   - Use quantized models (INT8/INT4) when possible
   - Consider ONNX Runtime for faster inference

2. **Deployment Pattern**
   - Sidecar for tight integration (default)
   - Proxy for centralized management
   - Support both patterns

3. **Latency Optimization**
   - Batch processing for multiple requests
   - Model quantization
   - GPU sharing for guardrails (can use same GPU partition)

4. **Privacy & Compliance**
   - Configurable logging (can disable for sensitive data)
   - PII redaction in logs
   - Audit trail for compliance

### 2.5 Guardrail Catalog

Create a catalog of pre-configured guardrail models:

```yaml
guardrail_catalog:
  toxicity:
    - model_id: "unitary/toxic-bert"
      size: "140M"
      latency_ms: 20
      accuracy: 0.92
  pii:
    - model_id: "dslim/bert-base-NER"
      size: "440M"
      latency_ms: 35
      supported_entities: [SSN, EMAIL, PHONE, CREDIT_CARD]
  prompt_injection:
    - model_id: "protectai/deberta-v3-base-prompt-injection-v2"
      size: "184M"
      latency_ms: 25
      accuracy: 0.89
```

### 2.6 Success Criteria

- [ ] Deploy guardrail as sidecar with <50ms latency overhead
- [ ] Support 4+ guardrail types (toxicity, PII, prompt injection, NSFW)
- [ ] Configurable thresholds and policies
- [ ] Metrics exposed via Prometheus
- [ ] Integration with AIM InferenceService CRD

---

## 3. AIM Fine-Tuning Microservice Prototype

### 3.1 Architecture Overview

**Objective**: Containerized fine-tuning service compatible with AIM profiles, supporting LoRA, QLoRA, and full fine-tuning with automated profile generation.

### 3.2 Technical Approach

#### Phase 1: Core Fine-Tuning Service (Weeks 1-4)
- **Fine-Tuning Container**
  - AIM-compatible container using AIM Build patterns
  - Support for multiple frameworks:
    - **PEFT** (Parameter-Efficient Fine-Tuning) for LoRA/QLoRA
    - **Transformers** for full fine-tuning
    - **Axolotl** or **LLaMA-Factory** as training frameworks

- **Training Methods** (P0)
  - **LoRA**: Configurable rank, alpha, target modules
  - **QLoRA**: 4-bit and 8-bit quantization with LoRA
  - **Full Fine-Tuning**: For maximum customization

- **Dataset Support**
  - JSONL format (conversation format)
  - CSV format
  - HuggingFace Datasets integration
  - Automatic validation and preprocessing

- **AIM Profile Integration**
  - Read base model AIM profile
  - Generate fine-tuned model profile automatically
  - Update resource requirements based on fine-tuned model size

#### Phase 2: Job Management (Weeks 5-6)
- **KServe CRD for Fine-Tuning Jobs**
  ```yaml
  apiVersion: aim.amd.com/v1alpha1
  kind: FineTuningJob
  metadata:
    name: llama-3-finetune
  spec:
    baseModel:
      modelId: "meta-llama/Llama-3.1-8B-Instruct"
      profile: "llama-3.1-8b-instruct"
    method: "lora"  # or "qlora", "full"
    dataset:
      source: "s3://bucket/training-data.jsonl"
      format: "jsonl"
    hyperparameters:
      learningRate: 2e-4
      batchSize: 4
      epochs: 3
      loraRank: 16
      loraAlpha: 32
    output:
      registry: "harbor.example.com/aim-models"
      profile: "auto-generate"
  ```

- **Job Lifecycle Management**
  - Create, monitor, pause, resume, delete jobs
  - Checkpoint management (save, version, restore)
  - Automatic retry on failure

#### Phase 3: Advanced Features (Weeks 7-10)
- **Checkpoint Management**
  - Automatic checkpoint saving (configurable intervals)
  - Version control for checkpoints
  - Upload to model registry (Harbor, HuggingFace)
  - Resume from checkpoint

- **Monitoring & Metrics**
  - Training metrics: Loss, learning rate, GPU utilization
  - Expose via Prometheus
  - K8s events for job status
  - TensorBoard integration

- **Validation Framework**
  - Test dataset validation
  - Automated quality checks
  - Model comparison tools

- **Hyperparameter Optimization** (P1)
  - Integration with Optuna or Ray Tune
  - Automated hyperparameter search
  - Cost-aware optimization

### 3.3 Prototype Structure

```
aim-finetuning/
├── finetuning/
│   ├── base/
│   │   ├── Dockerfile           # Base fine-tuning container
│   │   ├── app.py              # Training orchestration
│   │   └── trainer_base.py     # Base trainer class
│   ├── methods/
│   │   ├── lora_trainer.py     # LoRA implementation
│   │   ├── qlora_trainer.py    # QLoRA implementation
│   │   └── full_trainer.py     # Full fine-tuning
│   ├── dataset/
│   │   ├── loader.py           # Dataset loading
│   │   ├── preprocessor.py    # Data preprocessing
│   │   └── validator.py       # Dataset validation
│   └── profile/
│       ├── generator.py        # AIM profile generation
│       └── validator.py       # Profile validation
├── k8s/
│   ├── crd/
│   │   └── finetuning-job-crd.yaml
│   ├── controller/
│   │   └── finetuning-controller.py
│   └── operator/
│       └── finetuning-operator.yaml
├── checkpoint/
│   ├── manager.py              # Checkpoint management
│   └── storage.py              # Storage backends
├── monitoring/
│   ├── metrics.py
│   └── dashboards/
└── templates/
    └── common-configs/         # Template library
        ├── chat.yaml
        ├── code.yaml
        └── summarization.yaml
```

### 3.4 Key Technical Decisions

1. **Training Framework**
   - Use **PEFT** library for LoRA/QLoRA (HuggingFace)
   - Use **Transformers** Trainer API for consistency
   - Consider **Axolotl** for advanced features

2. **Model Architecture Support**
   - Start with Llama, Mistral, Qwen, Gemma (P0)
   - Extensible architecture for adding new models
   - Auto-detect architecture from model config

3. **Resource Management**
   - Configurable GPU memory limits
   - Automatic batch size adjustment based on available memory
   - Support for gradient checkpointing for memory efficiency

4. **Profile Generation**
   - Analyze fine-tuned model size
   - Estimate memory requirements
   - Generate optimal vLLM configuration
   - Include fine-tuning metadata in profile

5. **Distributed Training** (P1)
   - Support DeepSpeed ZeRO for multi-GPU
   - FSDP (Fully Sharded Data Parallel) support
   - Multi-node training via K8s

### 3.5 Fine-Tuning Template Library

Create common templates for popular use cases:

```yaml
# templates/chat.yaml
method: lora
hyperparameters:
  learningRate: 2e-4
  batchSize: 4
  epochs: 3
  loraRank: 16
  loraAlpha: 32
  targetModules: ["q_proj", "v_proj", "k_proj", "o_proj"]
dataset:
  format: "conversation"
  systemPrompt: "You are a helpful assistant."
```

### 3.6 Success Criteria

- [ ] Deploy fine-tuning job via KServe CRD
- [ ] Support LoRA, QLoRA, and full fine-tuning
- [ ] Generate AIM profile automatically for fine-tuned model
- [ ] Checkpoint management with versioning
- [ ] Training metrics via Prometheus
- [ ] Resume from checkpoint
- [ ] Support 5+ model architectures

---

## 4. Integration & Cross-Feature Considerations

### 4.1 GPU Sharing + Guardrails
- Guardrails can share GPU partitions with inference models
- Smaller guardrail models (<1B) can run in same partition as larger inference model
- Resource allocation: Reserve small partition (2-4GB) for guardrails

### 4.2 Fine-Tuning + Guardrails
- Fine-tuned models should pass guardrails before deployment
- Validation framework can use guardrails for quality checks
- Guardrail fine-tuning integration (P2)

### 4.3 Fine-Tuning + GPU Sharing
- Fine-tuning jobs can use GPU partitions
- Support fine-tuning multiple models concurrently on partitioned GPU
- Resource scheduling between inference and fine-tuning

### 4.4 Unified AIM Profile Format

Extend AIM profile to support all features:

```json
{
  "model_id": "meta-llama/Llama-3.1-8B-Instruct",
  "version": "1.0.0",
  "gpu_sharing": {
    "enabled": true,
    "memory_limit_gb": 40,
    "partition_id": 0,
    "qos_priority": "high"
  },
  "guardrails": [
    {
      "type": "toxicity",
      "threshold": 0.3,
      "deployment": "sidecar"
    }
  ],
  "finetuning": {
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "method": "lora",
    "checkpoint": "harbor.example.com/aim-models/llama-3-finetuned:v1"
  }
}
```

---

## 5. Prototype Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] GPU Sharing: Basic memory partitioning
- [ ] Guardrails: Core microservice + 2 guardrail types
- [ ] Fine-Tuning: Basic LoRA support + profile generation

### Phase 2: Integration (Weeks 5-8)
- [ ] GPU Sharing: KServe CRD integration
- [ ] Guardrails: Sidecar deployment + KServe integration
- [ ] Fine-Tuning: KServe CRD + checkpoint management

### Phase 3: Advanced Features (Weeks 9-12)
- [ ] GPU Sharing: QoS + monitoring
- [ ] Guardrails: Multi-guardrail orchestration + advanced types
- [ ] Fine-Tuning: QLoRA + validation framework

### Phase 4: Production Readiness (Weeks 13-16)
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Performance optimization
- [ ] Security hardening

---

## 6. Technology Stack Recommendations

### Core Technologies
- **Container Runtime**: Docker/containerd
- **Orchestration**: Kubernetes + KServe
- **GPU Framework**: ROCm 6.x
- **Inference**: vLLM (primary), SGLang (secondary)
- **Training**: PEFT, Transformers, PyTorch

### Supporting Technologies
- **API Framework**: FastAPI (guardrails, fine-tuning)
- **Monitoring**: Prometheus + Grafana
- **Storage**: S3-compatible (checkpoints, datasets)
- **Model Registry**: Harbor, HuggingFace Hub
- **Service Mesh**: Istio (optional, for guardrail proxy)

### Development Tools
- **Testing**: pytest, pytest-k8s
- **Linting**: ruff, black, mypy
- **CI/CD**: GitHub Actions
- **Documentation**: Sphinx, MkDocs

---

## 7. Risk Mitigation

### Technical Risks
1. **ROCm Memory Partitioning Complexity**
   - Mitigation: Start with static partitioning, validate with AMD
   - Fallback: Use container-level isolation if partitioning unavailable

2. **Guardrail Latency**
   - Mitigation: Aggressive quantization, batch processing, GPU acceleration
   - Fallback: Async processing with caching

3. **Fine-Tuning Profile Generation Accuracy**
   - Mitigation: Extensive testing, validation framework
   - Fallback: Manual profile override option

### Operational Risks
1. **Resource Conflicts**
   - Mitigation: Comprehensive validation, resource scheduling
   - Monitoring and alerting

2. **Model Compatibility**
   - Mitigation: Extensive testing matrix, clear compatibility matrix
   - Version pinning for stability

---

## 8. Success Metrics

### GPU Sharing
- Multi-model deployment success rate: >95%
- Latency degradation: <10% vs. dedicated GPU
- Memory isolation: 100% (no cross-partition leaks)

### Guardrails
- Latency overhead: <50ms per request
- False positive rate: <5%
- Coverage: Support 4+ guardrail types

### Fine-Tuning
- Profile generation accuracy: >95%
- Training job success rate: >90%
- Checkpoint resume success: 100%

---

## 9. Next Steps

1. **Review & Approval**: Review this document with stakeholders
2. **Repository Setup**: Create three new repositories or branches:
   - `aim-gpu-sharing`
   - `aim-guardrails`
   - `aim-finetuning`
3. **Team Assignment**: Assign teams/resources for each feature
4. **Kickoff**: Begin Phase 1 implementation
5. **Weekly Sync**: Establish weekly progress reviews

---

## Appendix A: Reference Implementations

### GPU Sharing
- Reference architectures for GPU partitioning
- AMD GPU Partitioning documentation
- vLLM multi-model serving examples

### Guardrails
- HuggingFace Transformers safety tools
- AWS Bedrock guardrails
- Azure AI Content Safety

### Fine-Tuning
- HuggingFace PEFT examples
- Axolotl training framework
- LLaMA-Factory

---

## Appendix B: AIM Profile Schema Extensions

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "model_id": {"type": "string"},
    "gpu_sharing": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "memory_limit_gb": {"type": "number"},
        "partition_id": {"type": "integer"},
        "qos_priority": {"type": "string", "enum": ["low", "medium", "high"]}
      }
    },
    "guardrails": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string"},
          "threshold": {"type": "number"},
          "deployment": {"type": "string", "enum": ["sidecar", "proxy"]}
        }
      }
    },
    "finetuning": {
      "type": "object",
      "properties": {
        "base_model": {"type": "string"},
        "method": {"type": "string", "enum": ["lora", "qlora", "full"]},
        "checkpoint": {"type": "string"}
      }
    }
  }
}
```

