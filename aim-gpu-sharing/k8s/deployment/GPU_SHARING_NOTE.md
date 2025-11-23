# GPU Sharing in Kubernetes - Important Note

## Resource Allocation Issue

When deploying multiple vLLM instances on a single GPU node, Kubernetes resource allocation can prevent scheduling.

### The Problem

If both deployments request `amd.com/gpu: "1"`:
- First pod: Allocates 1 GPU
- Second pod: Cannot be scheduled (no GPU available)
- Result: Second pod stuck in `Pending` with "Insufficient amd.com/gpu"

### The Solution

For GPU sharing (SPX mode), remove the GPU resource request from the second deployment:

**First Instance (can keep GPU request):**
```yaml
resources:
  requests:
    amd.com/gpu: "1"
  limits:
    amd.com/gpu: "1"
```

**Second Instance (remove GPU request):**
```yaml
resources:
  requests:
    cpu: "4"
    memory: "16Gi"
  limits:
    cpu: "8"
    memory: "32Gi"
  # No amd.com/gpu request - will share GPU with first instance
```

### Why This Works

1. **Device Access**: Both pods still have access to `/dev/kfd` and `/dev/dri` via nodeSelector
2. **GPU Sharing**: In SPX mode, multiple processes can share the same GPU partition
3. **Memory Management**: vLLM's `--gpu-memory-utilization` controls memory usage per instance
4. **Kubernetes**: Without GPU resource request, Kubernetes doesn't enforce exclusive allocation

### Alternative: GPU Time-Slicing (Future)

For better isolation, consider implementing GPU time-slicing or using CPX mode with multiple partitions.

### Current Configuration

- **First Instance**: `vllm-model-deployment.yaml` - Has GPU request (exclusive)
- **Second Instance**: `vllm-model-deployment-2.yaml` - No GPU request (shared)

Both instances will:
- Access the same GPU device
- Share GPU memory (controlled by `--gpu-memory-utilization`)
- Run concurrently on the same partition

