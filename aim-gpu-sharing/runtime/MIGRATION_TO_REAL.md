# Migration from Simulation to Real Hardware

## Current Status

The original `rocm_partitioner.py` was a **simulation/mockup** for development. We now have `rocm_partitioner_real.py` that uses **actual ROCm partitioning APIs** based on the [AMD MI300 partition modes guide](https://rocm.blogs.amd.com/software-tools-optimization/compute-memory-modes/).

## Key Differences

### Simulation (`rocm_partitioner.py`)
- ❌ No actual hardware interaction
- ❌ Manual memory tracking only
- ✅ Works without GPU hardware
- ✅ Good for development/testing

### Real Implementation (`rocm_partitioner_real.py`)
- ✅ Uses `amd-smi` commands
- ✅ Configures actual partition modes (CPX, NPS4)
- ✅ Creates real logical devices
- ✅ Works on physical MI300 hardware
- ❌ Requires ROCm installation and GPU access

## Migration Steps

### 1. Update Imports

**Before:**
```python
from rocm_partitioner import ROCmPartitioner
```

**After:**
```python
from rocm_partitioner_real import (
    ROCmPartitionerReal,
    ComputePartitionMode,
    MemoryPartitionMode
)
```

### 2. Update Initialization

**Before (Simulation):**
```python
partitioner = ROCmPartitioner(gpu_id=0)
partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])  # Manual sizes
```

**After (Real):**
```python
partitioner = ROCmPartitionerReal(gpu_id=0)
partitioner.initialize(
    gpu_name="MI300X",
    compute_mode=ComputePartitionMode.CPX,  # 8 logical devices
    memory_mode=MemoryPartitionMode.NPS4    # ~48GB per device
)
```

### 3. Partition Sizes

**Simulation**: You specify exact partition sizes manually.

**Real**: Partition sizes are determined by:
- **CPX + NPS4**: 8 devices, ~48GB each (192GB / 4)
- **CPX + NPS1**: 8 devices, 192GB each (all see full memory)
- **SPX + NPS1**: 1 device, 192GB

### 4. Environment Variables

**Real implementation** provides proper environment variables:

```python
env_vars = partitioner.get_environment_variables(partition_id=0)
# Returns:
# {
#   'ROCR_VISIBLE_DEVICES': '0',  # Logical device ID
#   'AIM_PARTITION_ID': '0',
#   'AIM_COMPUTE_MODE': 'CPX',
#   'AIM_MEMORY_MODE': 'NPS4',
#   'AIM_XCD_ID': '0'
# }
```

### 5. Check Hardware Availability

**Real implementation** checks for `amd-smi`:

```python
partitioner = ROCmPartitionerReal(gpu_id=0)
if not partitioner.amd_smi_available:
    logger.error("amd-smi not available - cannot use real partitioning")
    # Fall back to simulation or error
```

## Code Example: Full Migration

### Before (Simulation)

```python
from rocm_partitioner import ROCmPartitioner
from model_scheduler import ModelScheduler

# Initialize
partitioner = ROCmPartitioner(gpu_id=0)
partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])

# Schedule models
scheduler = ModelScheduler(partitioner)
scheduler.schedule_model("meta-llama/Llama-3.1-8B-Instruct")
```

### After (Real Hardware)

```python
from rocm_partitioner_real import (
    ROCmPartitionerReal,
    ComputePartitionMode,
    MemoryPartitionMode
)
from model_scheduler import ModelScheduler

# Initialize with real partition modes
partitioner = ROCmPartitionerReal(gpu_id=0)

# Check hardware availability
if not partitioner.amd_smi_available:
    raise RuntimeError("amd-smi not available - need physical GPU")

# Set partition modes (CPX/NPS4 for multi-model)
success = partitioner.initialize(
    gpu_name="MI300X",
    compute_mode=ComputePartitionMode.CPX,  # 8 devices
    memory_mode=MemoryPartitionMode.NPS4     # ~48GB each
)

if not success:
    raise RuntimeError("Failed to initialize partitions")

# Verify logical devices
devices = partitioner.get_logical_devices()
print(f"Created {len(devices)} logical devices")

# Schedule models (same API)
scheduler = ModelScheduler(partitioner)
scheduler.schedule_model("meta-llama/Llama-3.1-8B-Instruct", partition_id=0)

# Get environment for container deployment
env_vars = partitioner.get_environment_variables(partition_id=0)
```

## Testing Strategy

### Development/CI (No GPU)
- Use `rocm_partitioner.py` (simulation)
- Fast, no hardware required
- Good for unit tests

### Production/Physical Hardware
- Use `rocm_partitioner_real.py`
- Requires ROCm and `amd-smi`
- Validates on actual hardware

### Hybrid Approach

```python
import os

# Choose implementation based on environment
if os.environ.get("USE_REAL_PARTITIONING", "false").lower() == "true":
    from rocm_partitioner_real import ROCmPartitionerReal as ROCmPartitioner
else:
    from rocm_partitioner import ROCmPartitioner

# Rest of code works the same
partitioner = ROCmPartitioner(gpu_id=0)
```

## Validation Checklist

Before deploying to production:

- [ ] `amd-smi` is installed and accessible
- [ ] ROCm is properly installed
- [ ] GPU is MI300 series (MI300X, MI325X, etc.)
- [ ] Partition modes can be set successfully
- [ ] Logical devices appear in `amd-smi -l`
- [ ] Environment variables are correct
- [ ] Models can be allocated to partitions
- [ ] Memory limits are enforced

## Troubleshooting

### "amd-smi not available"
```bash
# Install ROCm
# Verify installation
which amd-smi
amd-smi --version
```

### "Failed to set partition mode"
- Requires root/admin privileges
- GPU may need to be reset
- Check GPU is in correct state

### "NPS4 requires CPX"
- Set compute mode to CPX first
- Then set memory mode to NPS4

## Next Steps

1. **Update ModelScheduler** to work with both implementations
2. **Add hardware detection** to auto-select implementation
3. **Update tests** to test both simulation and real modes
4. **Document deployment** requirements
5. **Test on physical hardware**

## References

- [AMD MI300 Partition Modes Guide](https://rocm.blogs.amd.com/software-tools-optimization/compute-memory-modes/)
- [ROCm Documentation](https://rocm.docs.amd.com/)
- [amd-smi Documentation](https://rocm.docs.amd.com/projects/amdsmi/en/latest/)

