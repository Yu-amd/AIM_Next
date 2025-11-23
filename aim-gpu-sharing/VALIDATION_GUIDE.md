# GPU Sharing/Partitioning Validation Guide

This guide provides comprehensive status checks to validate that GPU sharing and partitioning is actually working when applications are deployed via Docker or Kubernetes.

## Overview

When vLLM models are deployed, you need to verify:
1. **GPU partitions are created** - Partitions exist and are configured
2. **Models are using partitions** - Applications are assigned to specific partitions
3. **Resource isolation** - Each partition has isolated memory/compute
4. **Multi-model support** - Multiple models can run on same GPU
5. **Partition utilization** - Resources are being used correctly

---

## Prerequisites

```bash
# Install amd-smi (if not already available)
# Usually comes with ROCm installation

# Verify amd-smi works
amd-smi

# Check partitioner tools
python3 -c "from runtime.rocm_partitioner_real import ROCmPartitionerReal; print('Partitioner available')"
```

---

## Validation Method 1: Docker Deployment

### Step 1: Check GPU Partition Status

```bash
# Check current partition mode
amd-smi --show-compute-partition

# Expected output for CPX mode:
# Compute Partition: CPX
# Or for SPX mode:
# Compute Partition: SPX

# Check memory partition
amd-smi --show-memory-partition

# Check logical devices (partitions)
amd-smi -L
# Should show multiple devices if in CPX mode
```

### Step 2: Check Container GPU Access

```bash
# Check if container can see GPU
docker exec vllm-server amd-smi 2>/dev/null || echo "amd-smi not available in container"

# Check GPU devices in container
docker exec vllm-server ls -l /dev/kfd /dev/dri

# Check GPU memory usage
docker exec vllm-server amd-smi --showmeminfo
```

### Step 3: Verify Partition Assignment

```bash
# Check if partition ID is set
docker exec vllm-server env | grep -i partition

# Check GPU memory utilization per partition
amd-smi --showmeminfo vram

# Monitor GPU utilization
watch -n 1 'amd-smi --showmeminfo vram'
```

### Step 4: Multi-Model Validation

```bash
# Deploy second model on different partition
docker run -d --name vllm-server-2 \
  --device=/dev/kfd --device=/dev/dri \
  -p 8002:8000 \
  -e AIM_PARTITION_ID=1 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 8000

# Check both containers are using GPU
docker stats vllm-server vllm-server-2 --no-stream | grep -E "NAME|vllm"

# Verify both can run concurrently
curl http://localhost:8001/v1/models &
curl http://localhost:8002/v1/models &
```

### Step 5: Resource Isolation Check

```bash
# Check memory usage per partition
amd-smi --showmeminfo vram

# Monitor partition utilization
watch -n 1 'amd-smi --showmeminfo vram | grep -A 10 "Partition"'

# Check compute utilization per partition
amd-smi --showuse
```

---

## Validation Method 2: Kubernetes Deployment

### Step 1: Check GPU Partition Status on Node

```bash
# SSH to node or use kubectl exec
kubectl get nodes

# Check partition mode on node
amd-smi --show-compute-partition

# Check logical devices
amd-smi -L
```

### Step 2: Check Pod GPU Access

```bash
# Check pod can access GPU
kubectl exec -n aim-gpu-sharing -l app=vllm-model -- amd-smi 2>/dev/null || \
  echo "amd-smi not available in pod"

# Check GPU devices in pod
kubectl exec -n aim-gpu-sharing -l app=vllm-model -- ls -l /dev/kfd /dev/dri

# Check environment variables
kubectl exec -n aim-gpu-sharing -l app=vllm-model -- env | grep -i partition
```

### Step 3: Verify GPU Resource Allocation

```bash
# Check pod resource requests/limits
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model | grep -A 10 "Limits\|Requests"

# Should show:
# Limits:
#   amd.com/gpu: 1
# Requests:
#   amd.com/gpu: 1

# Check node GPU allocation
kubectl describe node <node-name> | grep -A 10 "Allocated resources"
# Should show GPU is allocated
```

### Step 4: Multi-Model Validation

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
        - name: AIM_PARTITION_ID
          value: "1"
        resources:
          requests:
            amd.com/gpu: "1"
          limits:
            amd.com/gpu: "1"
      nodeSelector:
        amd.com/gpu: "true"
EOF

# Check both pods are running
kubectl get pods -n aim-gpu-sharing

# Verify both can access GPU
kubectl exec -n aim-gpu-sharing -l app=vllm-model -- amd-smi &
kubectl exec -n aim-gpu-sharing -l app=vllm-model-2 -- amd-smi &
```

### Step 5: Check Partition Utilization

```bash
# Get GPU metrics from node
amd-smi --showmeminfo vram

# Check partition memory usage
amd-smi --showmeminfo vram | grep -A 5 "Partition"

# Monitor in real-time
watch -n 1 'amd-smi --showmeminfo vram'
```

---

## Comprehensive Validation Script

```bash
#!/bin/bash
# GPU Sharing Validation Script

echo "=========================================="
echo "GPU Sharing/Partitioning Validation"
echo "=========================================="
echo ""

# 1. Check partition mode
echo "1. GPU Partition Mode:"
amd-smi --show-compute-partition
echo ""

# 2. Check logical devices
echo "2. Logical Devices (Partitions):"
amd-smi -L
echo ""

# 3. Check memory partition
echo "3. Memory Partition Mode:"
amd-smi --show-memory-partition
echo ""

# 4. Check GPU memory usage
echo "4. GPU Memory Usage:"
amd-smi --showmeminfo vram
echo ""

# 5. Check running containers/pods
echo "5. Running vLLM Instances:"
if command -v docker &> /dev/null; then
    echo "Docker containers:"
    docker ps | grep vllm
fi
if command -v kubectl &> /dev/null; then
    echo "Kubernetes pods:"
    kubectl get pods -n aim-gpu-sharing -l app=vllm-model 2>/dev/null || echo "No pods found"
fi
echo ""

# 6. Check GPU utilization
echo "6. GPU Utilization:"
amd-smi --showuse
echo ""

# 7. Check partition assignment (if available)
echo "7. Partition Assignment:"
if command -v docker &> /dev/null; then
    docker ps --format "{{.Names}}" | grep vllm | while read name; do
        echo "Container: $name"
        docker exec $name env | grep -i partition || echo "  No partition ID set"
    done
fi
if command -v kubectl &> /dev/null; then
    kubectl get pods -n aim-gpu-sharing -l app=vllm-model -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].env[?(@.name=="AIM_PARTITION_ID")].value}{"\n"}{end}' 2>/dev/null || echo "No partition IDs found"
fi
echo ""

echo "=========================================="
echo "Validation Complete"
echo "=========================================="
```

---

## Expected Results

### SPX Mode (Single Partition)
- **Partitions**: 1 logical device
- **Memory**: 192GB total
- **Multi-model**: Models share the same partition
- **Validation**: All models show same GPU device

### CPX Mode (8 Partitions for MI300X)
- **Partitions**: 8 logical devices (one per XCD)
- **Memory**: ~24GB per partition (192GB / 8)
- **Multi-model**: Each model can use different partition
- **Validation**: Different models show different device IDs

---

## Key Validation Points

### ✅ Partition Creation
- [ ] `amd-smi` output shows partition mode (SPX/NPS1 or CPX/NPS4)
- [ ] Partition mode column shows correct mode
- [ ] Partitions are accessible from containers/pods

**Note:** Some amd-smi versions don't support `--show-compute-partition` flag. Use the main `amd-smi` output which shows partition mode in the table.

### ✅ Partition Assignment
- [ ] Environment variable `AIM_PARTITION_ID` is set (if using partitions)
- [ ] Applications can access assigned partition
- [ ] Multiple models can run on different partitions

### ✅ Resource Isolation
- [ ] Each partition shows separate memory usage
- [ ] Memory usage per partition is isolated
- [ ] Compute utilization is tracked per partition

### ✅ Multi-Model Support
- [ ] Multiple vLLM instances can run simultaneously
- [ ] Each instance can access its assigned partition
- [ ] No resource conflicts between models

### ✅ GPU Sharing Working
- [ ] Multiple models share same physical GPU
- [ ] Resources are partitioned correctly
- [ ] No single model monopolizes GPU

---

## Troubleshooting

### No Partitions Visible

```bash
# Check if partition mode is set
amd-smi --show-compute-partition

# If SPX, you'll only see 1 device
# If CPX, you should see 8 devices

# Check if CPX mode is supported
amd-smi --show-supported-compute-partition
```

### Partition Not Assigned

```bash
# Check if partition ID environment variable is set
docker exec vllm-server env | grep PARTITION
# or
kubectl exec -n aim-gpu-sharing -l app=vllm-model -- env | grep PARTITION

# If not set, applications will use default (all GPU)
```

### Multiple Models Not Working

```bash
# Check GPU memory availability
amd-smi --showmeminfo vram

# Check if models are actually using different partitions
# Each model should show different device ID in CPX mode

# Verify both models are running
docker ps | grep vllm
# or
kubectl get pods -n aim-gpu-sharing
```

---

## Advanced Validation

### Check Partition Memory Usage

```bash
# Detailed memory info per partition
amd-smi --showmeminfo vram

# Monitor continuously
watch -n 1 'amd-smi --showmeminfo vram'
```

### Check Compute Utilization

```bash
# GPU compute utilization
amd-smi --showuse

# Per-partition utilization (if available)
amd-smi --showuse --detail
```

### Validate with Metrics Exporter

```bash
# If metrics exporter is running
curl http://localhost:8080/metrics | grep -i partition

# Look for:
# - partition_memory_usage_bytes
# - partition_compute_utilization
# - model_partition_assignment
```

---

## Quick Validation Checklist

**For Docker:**
- [ ] `amd-smi --show-compute-partition` shows mode
- [ ] `amd-smi -L` shows correct number of devices
- [ ] Container can access GPU (`docker exec vllm-server amd-smi`)
- [ ] Multiple containers can run simultaneously
- [ ] Each container shows GPU usage

**For Kubernetes:**
- [ ] Pod has GPU resource request/limit
- [ ] Pod can access GPU (`kubectl exec ... amd-smi`)
- [ ] Node shows GPU allocated
- [ ] Multiple pods can run on same node
- [ ] Each pod shows GPU usage

**GPU Sharing Specific:**
- [ ] Multiple models running on same GPU
- [ ] Partition mode is set (SPX or CPX)
- [ ] Memory is partitioned correctly
- [ ] No resource conflicts
- [ ] Models can run concurrently

---

## Next Steps

After validation:
1. Monitor partition utilization over time
2. Test with different model sizes
3. Verify QoS guarantees (if implemented)
4. Check metrics in Prometheus/Grafana
5. Test partition switching (if supported)

