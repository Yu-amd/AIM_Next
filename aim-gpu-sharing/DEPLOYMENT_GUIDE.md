# Complete Deployment Guide - vLLM Model Serving

This guide provides step-by-step instructions for deploying vLLM models using both Docker and Kubernetes methods. Follow these instructions on a clean node to verify everything works.

## Prerequisites

### System Requirements
- Ubuntu 22.04+ or similar Linux distribution
- AMD GPU with ROCm support (e.g., MI300X)
- Docker installed and running
- Kubernetes cluster (for K8s deployment)
- kubectl configured
- Python 3.10+

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker info

# Check Kubernetes (if using K8s)
kubectl version --client
kubectl cluster-info

# Check Python
python3 --version

# Check GPU
amd-smi  
```

### Install Python Dependencies

```bash
# Install Flask and requests for web app
pip3 install flask requests --break-system-packages --ignore-installed blinker
```

---

## Method 1: Docker Deployment

### Step 1: Clean Up Any Existing Instances

```bash
# Stop and remove any existing vLLM containers
docker ps -a --filter "name=vllm" --format "{{.Names}}" | xargs -r docker stop
docker ps -a --filter "name=vllm" --format "{{.Names}}" | xargs -r docker rm

# Verify cleanup
docker ps -a | grep vllm
```

### Step 2: Verify ROCm Image Available

```bash
# Check if ROCm vLLM image exists
docker images | grep rocm

# If not available, you may need to pull it
# docker pull rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915
```

### Step 3: Run vLLM Container

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Create model cache directory
mkdir -p model-cache

# Run vLLM server
docker run -d --name vllm-server \
  --device=/dev/kfd \
  --device=/dev/dri \
  -p 8001:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.95
```

**Note:** The first run will download the model from HuggingFace, which can take 5-15 minutes depending on your connection.

### Step 4: Verify Container is Running

```bash
# Check container status
docker ps | grep vllm-server

# Check logs
docker logs -f vllm-server
```

Wait until you see logs indicating the server is ready (e.g., "Uvicorn running on http://0.0.0.0:8000").

### Step 5: Validate Deployment

```bash
# Test models endpoint
curl http://localhost:8001/v1/models

# Expected output: JSON with model information
# {
#   "object": "list",
#   "data": [{
#     "id": "Qwen/Qwen2.5-7B-Instruct",
#     ...
#   }]
# }

# Test chat completion
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello! Say hi back."}],
    "max_tokens": 50
  }'

# Expected output: JSON with assistant response
```

### Step 6: Deploy Web Application (Optional)

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Start web app
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

**For remote access:**
```bash
# On your local machine
ssh -L 5000:localhost:5000 -L 8001:localhost:8001 user@remote-node-ip

# Then open browser: http://localhost:5000
```

### Step 7: Cleanup (When Done)

```bash
# Stop and remove container
docker stop vllm-server
docker rm vllm-server

# Optional: Remove model cache
rm -rf model-cache
```

---

## Method 2: Kubernetes Deployment

### Step 1: Clean Up Any Existing Instances

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Use cleanup script
./k8s/deployment/cleanup-vllm.sh

# Or manually
kubectl delete deployment vllm-model-deployment -n aim-gpu-sharing 2>/dev/null
kubectl delete svc vllm-model-service -n aim-gpu-sharing 2>/dev/null
kubectl delete pvc model-cache-pvc -n aim-gpu-sharing 2>/dev/null

# Verify cleanup
kubectl get all -n aim-gpu-sharing
```

### Step 2: Verify Prerequisites

```bash
# Check cluster access
kubectl cluster-info

# Check node labels (GPU node should have amd.com/gpu label)
kubectl get nodes --show-labels | grep amd.com/gpu

# If node doesn't have label, add it
NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl label nodes $NODE_NAME amd.com/gpu=true --overwrite

# Verify GPU resources available
kubectl describe node $NODE_NAME | grep -A 5 "amd.com/gpu"
```

### Step 3: Verify Storage

```bash
# Check storage classes
kubectl get storageclass

# Check available PVs
kubectl get pv

# If using local-storage, ensure a PV is available (or create one)
```

### Step 4: Import Image to Containerd (If Needed)

Kubernetes uses containerd, not Docker. If the image is only in Docker:

```bash
# Export from Docker and import to containerd
docker save rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 | \
  sudo ctr -n k8s.io images import -

# Verify
sudo ctr -n k8s.io images list | grep rocm
```

**Note:** If you skip this step, Kubernetes will pull the image from the registry (takes 5-15 minutes for 35GB image).

### Step 5: Deploy vLLM Model

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Deploy model
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct
```

This will:
- Create namespace `aim-gpu-sharing`
- Create deployment with vLLM server
- Create service (NodePort on port 30080)
- Create PVC for model cache

### Step 6: Monitor Deployment

```bash
# Watch pod status
kubectl get pods -n aim-gpu-sharing -w

# Check deployment status
kubectl get deployment -n aim-gpu-sharing

# View pod logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model -f
```

**Expected timeline:**
- Pod creation: ~30 seconds
- Image pull (if needed): 5-15 minutes
- Model download: 5-15 minutes (first time only)
- Server ready: When you see "Uvicorn running on http://0.0.0.0:8000" in logs

### Step 7: Validate Deployment

```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Test via NodePort
curl http://${NODE_IP}:30080/v1/models

# Or use port-forward
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8002:8000 &
sleep 2
curl http://localhost:8002/v1/models

# Test chat completion
curl http://${NODE_IP}:30080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello! Say hi back."}],
    "max_tokens": 50
  }'
```

### Step 8: Deploy Web Application (Optional)

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Deploy web app to Kubernetes
./k8s/deployment/deploy-web-app.sh
```

**Access web app:**
```bash
# Port forward
kubectl port-forward -n aim-gpu-sharing svc/web-app-service 5000:5000

# Or via NodePort
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "Web UI: http://${NODE_IP}:30050"
```

### Step 9: Cleanup (When Done)

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Use cleanup script
./k8s/deployment/cleanup-vllm.sh

# Or manually
kubectl delete deployment vllm-model-deployment -n aim-gpu-sharing
kubectl delete svc vllm-model-service -n aim-gpu-sharing
kubectl delete pvc model-cache-pvc -n aim-gpu-sharing
```

---

## Validation Checklist

### Basic Deployment Validation

#### Docker Deployment
- [ ] Container is running (`docker ps | grep vllm-server`)
- [ ] Container logs show server ready
- [ ] `/v1/models` endpoint returns model list
- [ ] `/v1/chat/completions` endpoint returns responses
- [ ] Web app can connect (if deployed)

#### Kubernetes Deployment
- [ ] Pod is in `Running` state (`kubectl get pods -n aim-gpu-sharing`)
- [ ] Pod logs show server ready
- [ ] Service is accessible (`kubectl get svc -n aim-gpu-sharing`)
- [ ] `/v1/models` endpoint returns model list (via NodePort or port-forward)
- [ ] `/v1/chat/completions` endpoint returns responses
- [ ] Web app can connect (if deployed)

### GPU Sharing/Partitioning Validation

**See [VALIDATION_GUIDE.md](./VALIDATION_GUIDE.md) for detailed GPU sharing validation procedures.**

Quick validation:
```bash
# Run validation script
./validate-gpu-sharing.sh
```

Key checks:
- [ ] Partition mode detected (SPX or CPX)
- [ ] Correct number of logical devices (1 for SPX, 8 for CPX on MI300X)
- [ ] Container/pod can access GPU (`amd-smi` works)
- [ ] Multiple models can run simultaneously (GPU sharing working)
- [ ] Partition assignment verified (if using partitions)
- [ ] Memory usage per partition is isolated
- [ ] No resource conflicts between models

---

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker logs vllm-server

# Check GPU access
amd-smi

# Check device permissions
ls -l /dev/kfd /dev/dri
```

**Port already in use:**
```bash
# Find what's using the port
lsof -i :8001

# Use different port
docker run ... -p 8002:8000 ...
```

### Kubernetes Issues

**Pod stuck in Pending:**
```bash
# Check why
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model

# Common issues:
# - Node label missing: kubectl label nodes <node> amd.com/gpu=true
# - PVC can't bind: Check storage class and PV availability
# - Insufficient resources: Check node resources
```

**Pod stuck in ContainerCreating:**
```bash
# Check events
kubectl get events -n aim-gpu-sharing --sort-by='.lastTimestamp' | tail -10

# Common issues:
# - Image pull taking time (normal for 35GB image, wait 5-15 min)
# - Import image to containerd to speed up
```

**Image pull errors:**
```bash
# Import from Docker to containerd
docker save rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 | \
  sudo ctr -n k8s.io images import -
```

**PVC can't bind:**
```bash
# Check PVC status
kubectl get pvc -n aim-gpu-sharing

# Check available PVs
kubectl get pv

# If PVC requests too much storage, delete and recreate with smaller size
kubectl delete pvc model-cache-pvc -n aim-gpu-sharing
# Then update deployment YAML with smaller PVC size (e.g., 50Gi instead of 200Gi)
```

---

## Quick Reference

### Docker Commands
```bash
# Start
docker run -d --name vllm-server --device=/dev/kfd --device=/dev/dri \
  -p 8001:8000 -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000

# Check
docker ps | grep vllm
docker logs -f vllm-server

# Test
curl http://localhost:8001/v1/models

# Stop
docker stop vllm-server && docker rm vllm-server
```

### Kubernetes Commands
```bash
# Deploy
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct

# Check
kubectl get pods -n aim-gpu-sharing
kubectl logs -n aim-gpu-sharing -l app=vllm-model -f

# Test
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
curl http://${NODE_IP}:30080/v1/models

# Cleanup
./k8s/deployment/cleanup-vllm.sh
```

---

## Next Steps

After successful deployment:
1. Test with CLI client: `python3 examples/cli/model_client.py --endpoint http://localhost:8001/v1`
2. Deploy web application: See `examples/README.md`
3. Integrate with GPU sharing: See `VLLM_INTEGRATION.md`
4. Set up monitoring: See `monitoring/` directory

