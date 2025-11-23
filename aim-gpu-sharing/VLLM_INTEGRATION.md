# vLLM Integration Guide

This document describes the vLLM integration for AIM GPU Sharing, based on the [AIM-Engine project](https://github.com/Yu-amd/aim-engine) workflow.

## Overview

The vLLM integration enables:
- Building ROCm vLLM containers for any HuggingFace model
- Deploying models to Kubernetes with GPU sharing support
- Serving models via OpenAI-compatible API
- CLI and web interfaces for model interaction

## Architecture

```
┌─────────────────────────────────────────────┐
│         Example Applications                │
│  ┌─────────────┐  ┌─────────────┐           │
│  │  CLI Client │  │  Web App    │           │
│  └─────────────┘  └─────────────┘           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      vLLM OpenAI-Compatible API             │
│      (http://localhost:8000/v1)              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      vLLM Server Container                  │
│  - ROCm vLLM runtime                        │
│  - GPU sharing partition support            │
│  - Model serving                            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Kubernetes Deployment                  │
│  - Pod with GPU resources                   │
│  - Persistent volume for model cache       │
│  - Service for external access              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      AMD GPU with Partitions                │
│  - GPU sharing enabled                      │
│  - Partition isolation                      │
└─────────────────────────────────────────────┘
```

## Components

### 1. Docker Container (`docker/Dockerfile.aim-vllm`)

Based on `rocm/vllm:latest` with:
- AIM GPU Sharing runtime components
- Convenience scripts (`aim-vllm-generate`, `aim-vllm-serve`)
- Model cache support
- GPU partition environment variables

**Build:**
```bash
./docker/build-vllm-container.sh
```

### 2. Kubernetes Deployment (`k8s/deployment/`)

- **model-deployment.yaml**: Complete deployment manifest
- **deploy-model.sh**: Automated deployment script

**Deploy:**
```bash
./k8s/deployment/deploy-model.sh <model-id> [partition-id]
```

### 3. Example Applications (`examples/`)

- **CLI Client** (`examples/cli/model_client.py`): Interactive command-line interface
- **Web Application** (`examples/web/web_app.py`): Modern web UI

## Workflow

### Step 1: Build Container

```bash
cd aim-gpu-sharing
./docker/build-vllm-container.sh
```

This creates `aim-gpu-sharing-vllm:latest` image.

### Step 2: Deploy Model

```bash
# Deploy default model (Llama-3.1-8B-Instruct)
./k8s/deployment/deploy-model.sh

# Deploy specific model
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct

# Deploy with GPU partition
./k8s/deployment/deploy-model.sh meta-llama/Llama-3.1-8B-Instruct 0
```

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -n aim-gpu-sharing

# Check logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model --tail=50

# Get endpoint
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
ENDPOINT="http://${NODE_IP}:30080/v1"

# Test endpoint
curl ${ENDPOINT}/models
```

### Step 4: Use Example Applications

**CLI Client:**
```bash
python3 examples/cli/model_client.py --endpoint ${ENDPOINT}
```

**Web Application:**
```bash
python3 examples/web/web_app.py --endpoint ${ENDPOINT} --port 5000
# Open http://localhost:5000 in browser
```

## Integration with GPU Sharing

### Partition Assignment

The deployment supports GPU sharing through environment variables:

```yaml
env:
- name: AIM_PARTITION_ID
  value: "0"  # GPU partition ID
```

### Resource Configuration

```yaml
resources:
  requests:
    amd.com/gpu: "1"
    memory: "16Gi"
    cpu: "4"
  limits:
    amd.com/gpu: "1"
    memory: "32Gi"
    cpu: "8"
```

### Integration with Partition Controller

The deployment can be integrated with the KServe partition controller:

1. Create InferenceService with GPU sharing annotations
2. Partition controller allocates partition
3. Deployment uses allocated partition via `AIM_PARTITION_ID`

## Model Support

Any HuggingFace model compatible with vLLM can be deployed:

- **Llama models**: `meta-llama/Llama-3.1-8B-Instruct`
- **Qwen models**: `Qwen/Qwen2.5-7B-Instruct`
- **Mistral models**: `mistralai/Mistral-7B-Instruct-v0.2`
- **And more...**

## API Usage

The vLLM endpoint provides OpenAI-compatible API:

### List Models
```bash
curl http://localhost:8000/v1/models
```

### Chat Completion
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### Streaming
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Troubleshooting

### Container Build Issues

**Problem:** Base image not found
```bash
# Pull base image first
docker pull rocm/vllm:latest
```

**Problem:** Build fails
```bash
# Check Docker is running
docker info

# Build with verbose output
docker build -f docker/Dockerfile.aim-vllm -t aim-gpu-sharing-vllm:latest . --progress=plain
```

### Deployment Issues

**Problem:** Pod stuck in Pending
```bash
# Check GPU resources
kubectl describe node | grep -A 10 "amd.com/gpu"

# Check pod events
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model
```

**Problem:** Model download fails
```bash
# Check logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model

# Check network connectivity
kubectl exec -n aim-gpu-sharing -it <pod-name> -- curl -I https://huggingface.co
```

### Endpoint Issues

**Problem:** Cannot connect to endpoint
```bash
# Check service
kubectl get svc -n aim-gpu-sharing

# Port forward for testing
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8000:8000

# Test locally
curl http://localhost:8000/v1/models
```

## Performance Considerations

### Memory Management

- Models are cached in persistent volume
- First deployment downloads model (can take time)
- Subsequent deployments use cached model

### GPU Utilization

- Set `--gpu-memory-utilization` based on partition size
- Monitor with metrics exporter
- Adjust based on model size and partition allocation

### Scaling

- Current deployment: 1 replica
- Can scale horizontally (multiple pods)
- Each pod requires GPU resource

## Next Steps

1. **Integrate with Partition Controller**
   - Automatic partition assignment
   - Dynamic partition management

2. **Multi-Model Deployment**
   - Deploy multiple models on same GPU
   - Use different partitions

3. **Performance Optimization**
   - Tune vLLM parameters
   - Optimize memory usage
   - Benchmark latency and throughput

## References

- [AIM-Engine Project](https://github.com/Yu-amd/aim-engine) - Original workflow
- [vLLM Documentation](https://docs.vllm.ai/)
- [ROCm vLLM](https://github.com/vllm-project/vllm) - ROCm support

