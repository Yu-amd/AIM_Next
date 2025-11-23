# Docker GPU Sharing Validation Guide

This guide provides step-by-step instructions for validating GPU sharing using Docker containers on AMD MI300X hardware.

## Prerequisites

- AMD MI300X GPU (or compatible AMD GPU)
- Docker installed and running
- ROCm vLLM container image available
- Model cache directory set up
- Sufficient GPU memory for multiple models

## Overview

Docker allows multiple containers to share the same GPU by bypassing Kubernetes resource allocation. This is the **only working method** for GPU sharing validation on systems with AMD GPU operator that doesn't support time-slicing.

## Step-by-Step Instructions

### Step 1: Prepare Environment

```bash
# Navigate to project directory
cd /root/AIM_Next/aim-gpu-sharing

# Ensure model cache directory exists
mkdir -p model-cache

# Check GPU availability
amd-smi | grep -E "SPX|CPX"
# Should show: SPX/NPS1 (1 partition, 192GB)
```

### Step 2: Stop Any Existing vLLM Containers

```bash
# List existing containers
docker ps -a --filter "name=vllm"

# Stop and remove existing containers
docker stop $(docker ps -q --filter "name=vllm") 2>/dev/null || true
docker rm $(docker ps -aq --filter "name=vllm") 2>/dev/null || true
```

### Step 3: Start First vLLM Instance

```bash
docker run -d --name vllm-instance-1 \
  --device=/dev/kfd \
  --device=/dev/dri \
  -p 8001:8000 \
  -v "$(pwd)/model-cache:/workspace/model-cache" \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.5
```

**Parameters:**
- `--name vllm-instance-1`: Container name
- `--device=/dev/kfd --device=/dev/dri`: GPU device access
- `-p 8001:8000`: Map host port 8001 to container port 8000
- `--gpu-memory-utilization 0.5`: Use 50% of GPU memory (allows room for second instance)

### Step 4: Wait for First Instance to Load

```bash
# Monitor logs
docker logs -f vllm-instance-1

# Wait for "Uvicorn running on" message (typically 2-3 minutes)
# Or check endpoint
curl http://localhost:8001/v1/models
```

**Expected output:**
```json
{
  "object": "list",
  "data": [{
    "id": "Qwen/Qwen2.5-7B-Instruct",
    ...
  }]
}
```

### Step 5: Start Second vLLM Instance

```bash
docker run -d --name vllm-instance-2 \
  --device=/dev/kfd \
  --device=/dev/dri \
  -p 8002:8000 \
  -v "$(pwd)/model-cache:/workspace/model-cache" \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.4
```

**Parameters:**
- `--name vllm-instance-2`: Second container name
- `-p 8002:8000`: Different port to avoid conflicts
- `--gpu-memory-utilization 0.4`: Use 40% of GPU memory
- **Total**: 50% + 40% = 90% (fits in 192GB with headroom)

### Step 6: Verify Both Instances Are Running

```bash
# Check container status
docker ps --filter "name=vllm-instance" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# NAMES              STATUS         PORTS
# vllm-instance-1   Up X minutes   0.0.0.0:8001->8000/tcp
# vllm-instance-2   Up X minutes   0.0.0.0:8002->8000/tcp
```

### Step 7: Test Both Endpoints

```bash
# Test first instance
curl http://localhost:8001/v1/models | python3 -m json.tool

# Test second instance
curl http://localhost:8002/v1/models | python3 -m json.tool

# Both should return model information
```

### Step 8: Verify GPU Sharing

```bash
# Check GPU processes
amd-smi | grep -A 20 "Processes"

# Expected output:
# | Processes:                                                                   |
# |  GPU        PID  Process Name          GTT_MEM  VRAM_MEM  MEM_USAGE     CU % |
# |==============================================================================|
# |    0     <PID1>  python3.10             X MB    XX.X GB    XX.X GB    X.X % |
# |    0     <PID2>  python3.10             X MB    XX.X GB    XX.X GB    X.X % |
# +------------------------------------------------------------------------------+
```

**Verification points:**
- ✅ Two `python3.10` processes visible
- ✅ Both processes using GPU memory
- ✅ Total memory usage < 192GB (SPX mode limit)

### Step 9: Test Concurrent Requests

```bash
# Send requests to both instances simultaneously
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello from instance 1"}],
    "max_tokens": 50
  }' &

curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello from instance 2"}],
    "max_tokens": 50
  }' &

wait

# Both requests should complete successfully
```

### Step 10: Monitor GPU Utilization

```bash
# Watch GPU utilization in real-time
watch -n 1 'amd-smi | grep -A 15 "Processes"'

# Check memory usage
amd-smi | grep "Mem-Usage"
# Should show total usage from both instances
```

## Validation Checklist

- [ ] Both containers running (`docker ps`)
- [ ] Both endpoints responding (`curl` to both ports)
- [ ] Two processes visible in `amd-smi`
- [ ] Total GPU memory < 192GB (for SPX mode)
- [ ] Concurrent requests work on both instances
- [ ] No errors in container logs

## Troubleshooting

### Issue: Port Already in Use

**Error:**
```
Error response from daemon: failed to bind host port for 0.0.0.0:8001: address already in use
```

**Solution:**
```bash
# Check what's using the port
sudo lsof -i :8001
# or
sudo netstat -tlnp | grep 8001

# Stop the process or use a different port
docker run ... -p 8003:8000 ...  # Use port 8003 instead
```

### Issue: Container Fails to Start

**Error:**
```
RuntimeError: Failed to infer device type
```

**Solution:**
```bash
# Verify GPU devices are accessible
ls -la /dev/kfd /dev/dri

# Check container has device access
docker exec vllm-instance-1 ls -la /dev/kfd /dev/dri

# Ensure devices are mounted correctly
docker run ... --device=/dev/kfd --device=/dev/dri ...
```

### Issue: Out of Memory

**Error:**
```
CUDA out of memory
```

**Solution:**
```bash
# Reduce memory utilization
--gpu-memory-utilization 0.3  # Instead of 0.5

# Or stop one instance to free memory
docker stop vllm-instance-1
```

### Issue: Model Loading Fails

**Error:**
```
Failed to load model
```

**Solution:**
```bash
# Check model cache
ls -la model-cache/

# Verify model is downloaded
docker exec vllm-instance-1 ls -la /workspace/model-cache

# Check container logs
docker logs vllm-instance-1
```

## Memory Allocation Guidelines

For SPX mode (192GB total):

| Instance | Memory Utilization | Approximate Memory |
|----------|-------------------|---------------|
| Instance 1 | 50% | ~96GB |
| Instance 2 | 40% | ~77GB |
| **Total** | **90%** | **~173GB** |
| **Headroom** | **10%** | **~19GB** |

**Recommendations:**
- Keep total utilization < 95% to avoid OOM errors
- Adjust based on model size
- Monitor actual usage with `amd-smi`

## Cleanup

```bash
# Stop all vLLM containers
docker stop vllm-instance-1 vllm-instance-2

# Remove containers
docker rm vllm-instance-1 vllm-instance-2

# Verify cleanup
docker ps -a --filter "name=vllm"
amd-smi | grep -A 15 "Processes"  # Should show no vLLM processes
```

## Advanced: Multiple Models

To test with different models:

```bash
# Instance 1: Qwen model
docker run -d --name vllm-qwen \
  --device=/dev/kfd --device=/dev/dri \
  -p 8001:8000 \
  -v "$(pwd)/model-cache:/workspace/model-cache" \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.5

# Instance 2: Different model (if available)
docker run -d --name vllm-other \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  -v "$(pwd)/model-cache:/workspace/model-cache" \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model <other-model-id> \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.4
```

## Expected Results

When GPU sharing is working correctly:

✅ **Container Status:**
- Both containers in `Up` state
- Both ports accessible

✅ **GPU Processes:**
- Two `python3.10` processes visible
- Both using GPU memory
- Total memory < partition limit

✅ **Endpoints:**
- Both `/v1/models` endpoints responding
- Both `/v1/chat/completions` endpoints working
- Concurrent requests succeed

✅ **Performance:**
- No significant degradation
- Both instances serve requests independently
- Memory isolation via vLLM's memory management

## Notes

- **SPX Mode**: Both instances share the same partition (192GB total)
- **No Isolation**: Models share compute resources (no hardware isolation)
- **Memory Management**: vLLM's `--gpu-memory-utilization` controls per-instance memory
- **Docker Only**: This method works because Docker bypasses Kubernetes resource allocation

## Related Documentation

- `GPU_SHARING_TEST_RESULTS.md` - Complete test results for all options
- `AMD_GPU_OPERATOR_LIMITATIONS.md` - Why Kubernetes doesn't support sharing
- `VALIDATION_GUIDE.md` - General validation procedures

