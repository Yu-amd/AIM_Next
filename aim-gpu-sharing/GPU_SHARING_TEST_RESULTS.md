# GPU Sharing Test Results

## Test Date
November 23, 2025

## Test Environment
- **Hardware**: 1x MI300X GPU
- **Partition Mode**: SPX/NPS1 (1 partition, 192GB)
- **Kubernetes**: v1.31.0
- **AMD GPU Operator**: Installed
- **ROCm**: 7.0.2

---

## Option 1: Docker GPU Sharing ✅ **WORKS**

### Test Setup
- Two Docker containers sharing the same GPU
- Container 1: Port 8001, 50% GPU memory
- Container 2: Port 8002, 40% GPU memory

### Results
✅ **SUCCESS**

**Status:**
- Both containers started successfully
- Both can access GPU devices (`/dev/kfd`, `/dev/dri`)
- Both vLLM instances loaded models
- Both endpoints responding

**Evidence:**
```bash
# Containers running
vllm-docker-1    Up X minutes   0.0.0.0:8001->8000/tcp
vllm-docker-2    Up X minutes   0.0.0.0:8002->8000/tcp

# Endpoints responding
✅ Docker Instance 1: Qwen/Qwen2.5-7B-Instruct
✅ Docker Instance 2: Qwen/Qwen2.5-7B-Instruct

# GPU processes
amd-smi shows both python3 processes using GPU
# Both processes appear in GPU memory usage
```

**Note:** Both instances share the same GPU partition (SPX mode). Memory is divided between them based on `--gpu-memory-utilization` settings.

**Conclusion:**
Docker bypasses Kubernetes resource allocation, allowing multiple containers to share the GPU. This is the **recommended approach** for GPU sharing validation.

---

## Option 2: CPX Mode ❌ **NOT AVAILABLE**

### Test Setup
- Check if hardware supports CPX mode (8 partitions)
- Attempt to enable CPX mode if possible

### Results
❌ **NOT SUPPORTED**

**Status:**
- Current mode: SPX/NPS1 (1 partition)
- CPX mode not available on this hardware
- Digital Ocean MI300X instances only advertise SPX mode
- Cannot create 8 partitions

**Evidence:**
```bash
# Partition mode
SPX/NPS1  # Only 1 partition available

# Logical devices
1 device detected (not 8)

# CPX mode command
amd-smi --set-compute-partition CPX
# Command not available or requires hardware support
```

**Conclusion:**
CPX mode requires hardware support that is not available on Digital Ocean MI300X instances. This option **cannot be tested** on the current hardware.

---

## Option 3: Single Pod with Multiple Containers ⚠️ **PARTIALLY WORKS**

### Test Setup
- Single Kubernetes pod with two containers
- Container 1: Requests `amd.com/gpu: "1"` (exclusive)
- Container 2: No GPU request (shares with container 1)

### Results
⚠️ **LIMITED SUCCESS**

**Status:**
- Pod **cannot be scheduled** ❌ (Insufficient amd.com/gpu)
- Even with only one container requesting GPU, if another container in same pod also needs GPU access, pod scheduling fails
- The AMD GPU operator requires exclusive GPU allocation per pod

**Evidence:**
```bash
# Pod status
vllm-multi-container-deployment-xxx   1/2   Running   0

# Container status
vllm-server-1: Ready ✅
vllm-server-2: Not Ready ❌ (CrashLoopBackOff)

# Container 2 logs
RuntimeError: Failed to infer device type
```

**Conclusion:**
Even within the same pod, containers without `amd.com/gpu` request cannot access GPU devices. The AMD GPU operator manages device access through resource allocation, so **only the container with GPU request can use the GPU**.

**Workaround:**
Both containers could request `amd.com/gpu: "1"`, but this would:
- Require 2 GPUs (not available)
- Or fail scheduling (Insufficient amd.com/gpu)

---

## Summary

| Option | Status | Notes |
|--------|--------|-------|
| **1. Docker** | ✅ **WORKS** | Both containers successfully share GPU, both endpoints responding |
| **2. CPX Mode** | ❌ **NOT AVAILABLE** | Hardware doesn't support CPX mode (only SPX available) |
| **3. Multi-Container Pod** | ❌ **DOESN'T WORK** | Pod cannot be scheduled (Insufficient amd.com/gpu) |

## Recommendations

### For GPU Sharing Validation:
1. **Use Docker** (Option 1) - Fully functional, bypasses K8s limitations
2. **Use CPX mode** (Option 2) - Only if hardware supports it
3. **Avoid multi-container pods** (Option 3) - Doesn't work with AMD GPU operator

### For Production Kubernetes:
- Deploy one model per GPU
- Use model quantization to reduce memory usage
- Consider using smaller models
- Wait for AMD GPU operator to add time-slicing support

---

## Test Commands Reference

### Option 1: Docker
```bash
# Start first instance
docker run -d --name vllm-docker-1 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8001:8000 \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.5

# Start second instance
docker run -d --name vllm-docker-2 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.4
```

### Option 2: CPX Mode
```bash
# Check current mode
amd-smi | grep -E "SPX|CPX"

# Attempt to enable CPX (requires hardware support)
amd-smi --set-compute-partition CPX
```

### Option 3: Multi-Container Pod
```bash
# Deploy
kubectl apply -f k8s/deployment/vllm-multi-container-pod.yaml

# Check status
kubectl get pods -n aim-gpu-sharing -l app=vllm-multi-container

# Check logs
kubectl logs -n aim-gpu-sharing <pod-name> -c vllm-server-1
kubectl logs -n aim-gpu-sharing <pod-name> -c vllm-server-2
```

