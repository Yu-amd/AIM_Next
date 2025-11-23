# AIM GPU Sharing - Examples

This directory contains example applications demonstrating model serving with vLLM integration.

## Overview

The examples show how to:
1. Build vLLM containers for models
2. Deploy models to Kubernetes with GPU sharing
3. Interact with deployed models via CLI and web interfaces

## Prerequisites

- Kubernetes cluster with AMD GPU operator
- Docker for building containers
- Python 3.10+ for example applications
- Python dependencies:
  ```bash
  pip3 install flask requests --break-system-packages
  ```

## Quick Start

### 1. Build vLLM Container

```bash
cd aim-gpu-sharing
./docker/build-vllm-container.sh
```

This builds a container image `aim-gpu-sharing-vllm:latest` based on the [AIM-Engine workflow](https://github.com/Yu-amd/aim-engine).

### 2. Deploy Model to Kubernetes

```bash
# Deploy a model (default: Qwen/Qwen2.5-7B-Instruct)
./k8s/deployment/deploy-model.sh

# Deploy a specific model
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct

# Deploy with GPU partition
./k8s/deployment/deploy-model.sh meta-llama/Llama-3.1-8B-Instruct 0
```

### 3. Test the Deployment

```bash
# Get endpoint URL
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
ENDPOINT="http://${NODE_IP}:30080/v1"

# Test with CLI
python3 examples/cli/model_client.py --endpoint $ENDPOINT

# Or start web interface
python3 examples/web/web_app.py --endpoint $ENDPOINT --port 5000
# Then open http://localhost:5000 in your browser
```

## Example Applications

### CLI Client (`examples/cli/model_client.py`)

Interactive command-line interface for chatting with deployed models.

**Features:**
- Interactive chat session
- Streaming responses
- Model auto-detection
- Single message mode

**Usage:**
```bash
# Interactive mode
python3 examples/cli/model_client.py --endpoint http://localhost:8000/v1

# List available models
python3 examples/cli/model_client.py --endpoint http://localhost:8000/v1 --list-models

# Single message
python3 examples/cli/model_client.py --endpoint http://localhost:8000/v1 --message "Hello, how are you?"
```

### Web Application (`examples/web/web_app.py`)

Modern web interface for interacting with deployed models.

**Features:**
- Beautiful, responsive UI
- Real-time chat interface
- Streaming support (future)
- Mobile-friendly

**Usage:**
```bash
# Start web server
python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 5000 --host 0.0.0.0

# For remote access, see REMOTE_ACCESS.md
```

**Remote Access:**
- **SSH Port Forwarding (Recommended):** `ssh -L 5000:localhost:5000 user@remote-node-ip`
- **Direct Access:** Open firewall and access via `http://remote-node-ip:5000`
- See [REMOTE_ACCESS.md](./REMOTE_ACCESS.md) for detailed instructions

## Docker Usage

### Run Container Locally

```bash
# Generate vLLM command
docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  -v $(pwd)/model-cache:/workspace/model-cache \
  aim-gpu-sharing-vllm:latest \
  aim-vllm-generate meta-llama/Llama-3.1-8B-Instruct

# Start vLLM server
docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  -v $(pwd)/model-cache:/workspace/model-cache \
  -p 8000:8000 \
  aim-gpu-sharing-vllm:latest \
  aim-vllm-serve meta-llama/Llama-3.1-8B-Instruct
```

## Kubernetes Deployment

### Manual Deployment

```bash
# Apply deployment manifest
kubectl apply -f k8s/deployment/model-deployment.yaml

# Check deployment status
kubectl get pods -n aim-gpu-sharing

# Get service endpoint
kubectl get svc -n aim-gpu-sharing
```

### Using Deployment Script

```bash
# Deploy with default model
./k8s/deployment/deploy-model.sh

# Deploy specific model
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct

# Deploy with GPU partition
./k8s/deployment/deploy-model.sh meta-llama/Llama-3.1-8B-Instruct 0
```

## Integration with GPU Sharing

The deployment supports GPU sharing through:

1. **Partition Assignment**: Set `AIM_PARTITION_ID` environment variable
2. **Resource Limits**: Configured in deployment manifest
3. **Partition Controller**: Can be integrated with KServe partition controller

## Troubleshooting

### Container Build Issues

```bash
# Check Docker is running
docker info

# Check base image availability
docker pull rocm/vllm:latest

# Build with verbose output
docker build -f docker/Dockerfile.aim-vllm -t aim-gpu-sharing-vllm:latest . --progress=plain
```

### Deployment Issues

```bash
# Check pod status
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model

# Check logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model --tail=50

# Check GPU resources
kubectl get nodes -o jsonpath='{.items[0].status.allocatable}'
```

### Endpoint Connection Issues

```bash
# Test endpoint directly
curl http://localhost:8000/v1/models

# Check service
kubectl get svc -n aim-gpu-sharing

# Port forward for testing
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8000:8000
```

## Next Steps

- Integrate with KServe partition controller
- Add GPU sharing partition assignment
- Implement multi-model deployment
- Add performance monitoring

