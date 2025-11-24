# AMD GPU Operator Limitations - GPU Sharing

## Current Situation

The AMD GPU operator appears to **not support GPU sharing/time-slicing** for multiple pods on a single GPU.

## Evidence

### 1. Resource Allocation Behavior

When deploying two pods requesting `amd.com/gpu: "1"`:
- **First pod**: Successfully allocated 1 GPU
- **Second pod**: Stuck in `Pending` with error: `Insufficient amd.com/gpu`

This indicates **exclusive allocation** - only one pod can claim the GPU resource.

### 2. Device Access Without Resource Request

When removing `amd.com/gpu` request from second pod:
- Pod can be scheduled ✅
- But vLLM cannot detect GPU ❌
- Error: `Failed to infer device type`

This suggests the AMD GPU operator manages device access through resource allocation.

### 3. Comparison with other GPU operators

**other GPU operators** supports:
- **Time-slicing**: Multiple pods can share a GPU with time-slicing
- **MIG**: Multi-Instance GPU for hardware partitioning
- **Configuration**: Via `DeviceClass` CRD

**AMD GPU Operator** (current):
- No time-slicing support found
- No `DeviceClass` CRD for configuration
- Exclusive allocation only

## Workarounds

### Option 1: Use SPX Mode with Memory Sharing (Not Pod-Level)

In SPX mode, you can run multiple processes on the same GPU partition, but:
- Must be in the **same pod** (multiple containers)
- Or use **Docker** directly (not Kubernetes)
- Kubernetes resource allocation prevents this at pod level

### Option 2: Use CPX Mode (If Available)

If hardware supports CPX mode:
- 8 partitions available
- Each partition can be allocated to a different pod
- Requires hardware support (not available on Digital Ocean MI300X)

### Option 3: Reduce First Instance Memory

Instead of two separate pods:
- Use one pod with reduced memory utilization
- Deploy multiple smaller models in same pod
- Or use model quantization to reduce memory

### Option 4: Wait for Operator Update

Future AMD GPU operator versions may add:
- Time-slicing support
- GPU sharing configuration
- DeviceClass CRD for sharing policies

## Current Recommendation

For **Kubernetes deployment** with AMD GPU operator:
- **Single pod per GPU** is the current limitation
- Use **Docker** for multi-instance GPU sharing (bypasses K8s resource allocation)
- Or use **CPX mode** if hardware supports it

## Testing Multi-Instance with Docker

Since Kubernetes doesn't support sharing, you can test GPU sharing with Docker:

```bash
# First instance
docker run -d --name vllm-1 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8001:8000 \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.5

# Second instance
docker run -d --name vllm-2 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.4
```

Both will share the GPU in SPX mode.

## Conclusion

**AMD GPU Operator does NOT currently support running two GPU pods on a single GPU** in Kubernetes.

The operator enforces exclusive GPU allocation per pod. For multi-instance GPU sharing:
- Use **Docker** (bypasses K8s resource management)
- Use **CPX mode** (if hardware supports)
- Use **single pod with multiple containers** (limited sharing)

