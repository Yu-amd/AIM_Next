# Deploy Second vLLM Instance for GPU Sharing Validation

⚠️ **IMPORTANT LIMITATION**: The AMD GPU operator does **NOT** support GPU sharing/time-slicing in Kubernetes. Only **one pod** can request `amd.com/gpu: "1"` at a time.

**For GPU sharing validation, use Docker instead of Kubernetes** (see below).

This guide shows how to deploy a second vLLM instance, but note the Kubernetes limitation.

## Prerequisites

- First vLLM instance already running
- Sufficient GPU memory (with reduced utilization, both models can fit)
- Kubernetes cluster with GPU support

## Quick Deploy

### Option 1: Use Deployment Script (Recommended)

```bash
cd /root/AIM_Next/aim-gpu-sharing
./k8s/deployment/deploy-second-model.sh
```

This will:
- Check for existing first instance
- Deploy second instance with 40% GPU memory utilization
- Create service on NodePort 30081
- Wait for deployment to be ready

### Option 2: Manual Deployment

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Apply deployment manifest
kubectl apply -f k8s/deployment/vllm-model-deployment-2.yaml

# Wait for pod to be ready
kubectl wait --for=condition=available \
  deployment/vllm-model-deployment-2 \
  -n aim-gpu-sharing \
  --timeout=300s

# Check status
kubectl get pods -n aim-gpu-sharing
```

## Configuration

### Memory Utilization

The second instance uses `--gpu-memory-utilization 0.4` (40%) to ensure both models fit:

- **First instance**: ~179GB (using most of 192GB)
- **Second instance**: ~40% = ~77GB
- **Total**: ~256GB (exceeds 192GB, so first instance needs reduction too)

**Important:** You may need to reduce the first instance's memory usage as well.

### Update First Instance Memory

```bash
# Scale down first instance
kubectl scale deployment vllm-model-deployment -n aim-gpu-sharing --replicas=0

# Update deployment to use less memory
kubectl set env deployment/vllm-model-deployment -n aim-gpu-sharing \
  VLLM_GPU_MEMORY_UTIL=0.5

# Or patch the deployment args
kubectl patch deployment vllm-model-deployment -n aim-gpu-sharing -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "vllm-server",
          "args": [
            "python3", "-m", "vllm.entrypoints.openai.api_server",
            "--model", "$(MODEL_ID)",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--gpu-memory-utilization", "0.5"
          ]
        }]
      }
    }
  }
}'

# Scale back up
kubectl scale deployment vllm-model-deployment -n aim-gpu-sharing --replicas=1
```

## Validation Steps

### 1. Check Both Pods Are Running

```bash
kubectl get pods -n aim-gpu-sharing
```

Expected:
```
NAME                                      READY   STATUS    RESTARTS   AGE
vllm-model-deployment-xxx                1/1     Running   0          ...
vllm-model-deployment-2-xxx               1/1     Running   0          ...
```

### 2. Check GPU Processes

```bash
amd-smi | grep -A 10 "Processes"
```

Expected: Both vLLM processes should appear

### 3. Test Both Endpoints

```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Test first instance
curl http://${NODE_IP}:30080/v1/models

# Test second instance
curl http://${NODE_IP}:30081/v1/models
```

### 4. Test Concurrent Requests

```bash
# Send requests to both simultaneously
curl http://${NODE_IP}:30080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello from instance 1"}],"max_tokens":50}' &

curl http://${NODE_IP}:30081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello from instance 2"}],"max_tokens":50}' &

wait
```

### 5. Check GPU Memory Usage

```bash
# Monitor GPU memory
watch -n 1 'amd-smi | grep -E "Mem-Usage|VRAM_MEM"'
```

Both models should show in the processes list, and total memory should be sum of both.

### 6. Run Validation Script

```bash
./validate-gpu-sharing.sh
```

Should show:
- ✅ Multiple vLLM instances detected
- ✅ Both instances running
- ✅ GPU sharing active

## Troubleshooting

### Pod Won't Start (Insufficient Resources)

**Issue:** Second pod stuck in Pending due to insufficient GPU memory

**Solution:** Reduce memory utilization for both instances:

```bash
# Update first instance
kubectl set env deployment/vllm-model-deployment -n aim-gpu-sharing \
  VLLM_GPU_MEMORY_UTIL=0.5

# Second instance already uses 0.4
```

### Both Models Using Too Much Memory

**Issue:** Total memory exceeds 192GB

**Solution:** Further reduce memory utilization:

```bash
# First instance: 50%
# Second instance: 40%
# Total: 90% = ~173GB (fits in 192GB)
```

### One Model Fails to Load

**Issue:** Out of memory error

**Solution:**
1. Check current memory usage: `amd-smi | grep Mem-Usage`
2. Reduce memory utilization further
3. Consider using smaller model or quantization

## Cleanup

```bash
# Delete second instance
kubectl delete deployment vllm-model-deployment-2 -n aim-gpu-sharing
kubectl delete svc vllm-model-service-2 -n aim-gpu-sharing

# Or use cleanup script
./k8s/deployment/cleanup-vllm.sh
```

## Expected Results

When both instances are running:

✅ **GPU Sharing Working:**
- Both pods in Running state
- Both show in `amd-smi` processes
- Both endpoints respond
- Concurrent requests work
- Total memory < 192GB

✅ **SPX Mode (Current Setup):**
- Both models share same partition
- Memory is divided between models
- No isolation (models share resources)
- Both can run concurrently

## Alternative: Use Docker for GPU Sharing

Since Kubernetes doesn't support GPU sharing with AMD GPU operator, use Docker:

```bash
# First instance (already running in K8s or Docker)
# Second instance in Docker
docker run -d --name vllm-2 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.4
```

Both instances will share the GPU in SPX mode.

## Next Steps

After validating GPU sharing (with Docker):
1. Monitor resource usage over time
2. Test with different model sizes
3. Verify QoS guarantees (if implemented)
4. Check partition utilization metrics

See `AMD_GPU_OPERATOR_LIMITATIONS.md` for details on the Kubernetes limitation.

