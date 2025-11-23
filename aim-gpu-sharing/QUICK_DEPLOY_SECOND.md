# Quick Guide: Deploy Second vLLM Instance

## Current Situation
- First instance: Using 95% GPU memory (~179GB)
- Available: ~13GB (not enough for second model)
- Solution: Reduce first instance memory first

## Step-by-Step Instructions

### Step 1: Reduce First Instance Memory

**Option A: Scale down, update, scale up**

```bash
# 1. Scale down first instance
kubectl scale deployment vllm-model-deployment -n aim-gpu-sharing --replicas=0

# 2. Wait for pod to terminate
kubectl wait --for=delete pod -n aim-gpu-sharing -l app=vllm-model --timeout=60s

# 3. Patch deployment to use less memory
kubectl patch deployment vllm-model-deployment -n aim-gpu-sharing --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/args/0",
    "value": "echo \"Starting vLLM server for model: $MODEL_ID\"\npython3 -m vllm.entrypoints.openai.api_server \\\n  --model $MODEL_ID \\\n  --host 0.0.0.0 \\\n  --port 8000 \\\n  --gpu-memory-utilization 0.5"
  }
]'

# 4. Scale back up
kubectl scale deployment vllm-model-deployment -n aim-gpu-sharing --replicas=1

# 5. Wait for pod to be ready
kubectl wait --for=condition=available deployment/vllm-model-deployment -n aim-gpu-sharing --timeout=300s
```

**Option B: Direct edit (simpler)**

```bash
# Edit deployment
kubectl edit deployment vllm-model-deployment -n aim-gpu-sharing

# Find the args section and change:
# --gpu-memory-utilization 0.95
# to:
# --gpu-memory-utilization 0.5

# Save and exit - Kubernetes will automatically restart the pod
```

### Step 2: Deploy Second Instance

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Use the deployment script
./k8s/deployment/deploy-second-model.sh

# Or manually
kubectl apply -f k8s/deployment/vllm-model-deployment-2.yaml
```

### Step 3: Verify Both Are Running

```bash
# Check pods
kubectl get pods -n aim-gpu-sharing

# Check GPU processes
amd-smi | grep -A 10 "Processes"

# Test both endpoints
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
curl http://${NODE_IP}:30080/v1/models  # First instance
curl http://${NODE_IP}:30081/v1/models  # Second instance
```

### Step 4: Validate GPU Sharing

```bash
# Run validation script
./validate-gpu-sharing.sh

# Check memory usage
amd-smi | grep "Mem-Usage"
```

## Expected Results

✅ Both pods in Running state
✅ Both show in `amd-smi` processes list
✅ Both endpoints respond
✅ Total memory < 192GB
✅ Concurrent requests work

## Memory Allocation

- First instance: 50% = ~96GB
- Second instance: 40% = ~77GB
- Total: ~173GB (fits in 192GB with some headroom)
