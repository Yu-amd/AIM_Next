# GPU Sharing/Partitioning Status Checks

## Current Setup Status

Based on your node configuration:
- **GPU**: 1x MI300X
- **Partition Mode**: SPX/NPS1 (1 partition, 192GB total)
- **Current vLLM Instance**: 1 running in Kubernetes
- **Memory Usage**: ~179GB / 192GB (vLLM using most of available memory)

## Status Checks for GPU Sharing Validation

### 1. Partition Mode Verification

**Check partition mode:**
```bash
amd-smi | grep -E "SPX|CPX"
```

**Expected output:**
```
|   0       0       4        SPX/NPS1 | ...
```

**What it means:**
- **SPX mode**: Single partition, all 192GB available
- **CPX mode**: 8 partitions, ~24GB each (for MI300X)

**For your setup (SPX):**
- ✅ 1 partition detected
- ✅ All 192GB memory available to single partition
- ⚠️  Cannot test partition isolation (only 1 partition)
- ✅ Can test multi-model sharing (models share same partition)

### 2. GPU Access from Containers/Pods

**Docker:**
```bash
docker exec vllm-server amd-smi | head -10
```

**Kubernetes:**
```bash
POD_NAME=$(kubectl get pods -n aim-gpu-sharing -l app=vllm-model -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aim-gpu-sharing $POD_NAME -- amd-smi | head -10
```

**Expected:**
- Should show GPU information
- Should show partition mode (SPX/NPS1)
- Should show memory usage

**Validation:**
- ✅ Container/pod can access GPU
- ✅ GPU devices visible (`/dev/kfd`, `/dev/dri`)
- ✅ amd-smi works from inside container/pod

### 3. GPU Memory Usage

**Check current memory usage:**
```bash
amd-smi | grep -E "Mem-Usage|VRAM_MEM"
```

**From your output:**
```
188945/196288 MB
```

**What to check:**
- Current usage vs total available
- Memory usage per process (if multiple models)
- Memory isolation (in CPX mode with multiple partitions)

**For SPX mode:**
- All models share the same 192GB
- Total memory usage = sum of all model memory
- No isolation between models (they share partition)

### 4. Multi-Model Validation (GPU Sharing)

**To validate GPU sharing is working, deploy second model:**

#### Docker:
```bash
# Deploy second model on different port
docker run -d --name vllm-server-2 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.4  # Use less memory to fit both
```

#### Kubernetes:
```bash
# Deploy second model
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-model-deployment-2
  namespace: aim-gpu-sharing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-model-2
  template:
    metadata:
      labels:
        app: vllm-model-2
    spec:
      containers:
      - name: vllm-server
        image: rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915
        env:
        - name: MODEL_ID
          value: "Qwen/Qwen2.5-7B-Instruct"
        command: ["/bin/bash", "-c"]
        args:
          - |
            python3 -m vllm.entrypoints.openai.api_server \
              --model $MODEL_ID \
              --host 0.0.0.0 \
              --port 8000 \
              --gpu-memory-utilization 0.4
        resources:
          requests:
            amd.com/gpu: "1"
          limits:
            amd.com/gpu: "1"
      nodeSelector:
        amd.com/gpu: "true"
EOF
```

**Note:** With only 1 GPU, you'll need to reduce memory usage per model to fit both.

**Validation checks:**
```bash
# 1. Both instances running
docker ps | grep vllm
# or
kubectl get pods -n aim-gpu-sharing

# 2. Both can access GPU
docker exec vllm-server amd-smi &
docker exec vllm-server-2 amd-smi &

# 3. Both endpoints responding
curl http://localhost:8001/v1/models
curl http://localhost:8002/v1/models

# 4. GPU memory shows both processes
amd-smi | grep -A 10 "Processes"
```

**Expected in SPX mode:**
- Both models share same GPU
- Both show in `amd-smi` processes list
- Total memory usage = Model1 + Model2
- Both can run concurrently

### 5. Resource Isolation Check

**For SPX mode (your current setup):**
- ❌ No memory isolation (models share 192GB)
- ❌ No compute isolation (models share compute units)
- ✅ Models can run concurrently
- ✅ Memory is shared/divided between models

**For CPX mode (if available):**
- ✅ Memory isolation (each partition has ~24GB)
- ✅ Compute isolation (each partition has separate XCD)
- ✅ Models can use different partitions
- ✅ Better resource isolation

**Check isolation:**
```bash
# See all processes using GPU
amd-smi | grep -A 20 "Processes"

# Check memory per process
amd-smi | grep -E "VRAM_MEM|MEM_USAGE"
```

### 6. Partition Assignment (If Using Partitions)

**Check if partition ID is set:**
```bash
# Docker
docker exec vllm-server env | grep PARTITION

# Kubernetes
kubectl exec -n aim-gpu-sharing <pod-name> -- env | grep PARTITION
```

**For SPX mode:**
- Partition ID not critical (only 1 partition)
- All models use partition 0

**For CPX mode:**
- Each model should have different partition ID (0-7)
- Verify models are using different partitions

### 7. Concurrent Model Serving

**Test both models simultaneously:**
```bash
# Send requests to both models at same time
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello 1"}],"max_tokens":50}' &

curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello 2"}],"max_tokens":50}' &

wait
```

**Validation:**
- ✅ Both requests complete successfully
- ✅ Both models respond concurrently
- ✅ No resource conflicts
- ✅ GPU utilization increases (check `amd-smi --showuse`)

## Quick Validation Script

Run the automated validation:
```bash
./validate-gpu-sharing.sh
```

## Status Check Summary

### Current Status (SPX Mode, Single Instance)

| Check | Status | Notes |
|-------|--------|-------|
| Partition Mode | ✅ SPX/NPS1 | 1 partition, 192GB |
| GPU Access | ✅ Working | Pod can access GPU |
| Memory Usage | ✅ ~179GB/192GB | vLLM using most memory |
| Multi-Model | ⚠️ Not tested | Need second instance |
| GPU Sharing | ⚠️ Not validated | Deploy second model |

### To Fully Validate GPU Sharing

1. **Deploy second vLLM instance** (with reduced memory)
2. **Verify both run concurrently**
3. **Check both can serve requests**
4. **Monitor GPU memory usage** (should show both processes)
5. **Test concurrent requests** to both models

### Expected Results (SPX Mode)

When two models are running:
- Both show in `amd-smi` processes list
- Total memory: Model1 + Model2 < 192GB
- Both endpoints respond successfully
- Concurrent requests work
- GPU utilization increases

## Limitations in SPX Mode

With SPX mode (1 partition):
- ❌ Cannot test partition isolation
- ❌ Models share all resources
- ✅ Can test multi-model concurrent serving
- ✅ Can test memory sharing

For full partition isolation testing, CPX mode (8 partitions) is needed.

## Next Steps

1. **Deploy second model** with reduced memory
2. **Run validation script** to check status
3. **Test concurrent serving** from both models
4. **Monitor GPU resources** during concurrent requests
5. **Verify no conflicts** between models

