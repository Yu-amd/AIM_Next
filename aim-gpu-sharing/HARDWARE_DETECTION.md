# Hardware Detection and Auto-Selection

This document explains how the system automatically detects hardware and selects the appropriate partitioner implementation.

## Overview

The system now includes **automatic hardware detection** that:
- Detects available GPU hardware
- Checks for ROCm and `amd-smi` availability
- Identifies MI300 series GPUs that support partitioning
- Automatically selects simulation or real partitioner
- Works seamlessly with ModelScheduler

## Components

### 1. HardwareDetector (`hardware_detector.py`)

Detects hardware capabilities:

```python
from hardware_detector import HardwareDetector

detector = HardwareDetector()

# Detect amd-smi
amd_smi_available = detector.detect_amd_smi()

# Detect ROCm
rocm_available = detector.detect_rocm()

# Detect GPU model
info = detector.detect_gpu(gpu_id=0)
print(f"GPU: {info.model_name}")
print(f"Supports partitioning: {info.supports_partitioning}")

# Get capability level
capability = detector.get_capability(gpu_id=0)
# Returns: REAL_PARTITIONING, SIMULATION, or NONE
```

### 2. Auto Partitioner (`auto_partitioner.py`)

Automatically creates the right partitioner:

```python
from auto_partitioner import create_partitioner, initialize_partitioner

# Auto-detect and create partitioner
partitioner = create_partitioner(gpu_id=0)

# Initialize with appropriate settings
initialize_partitioner(
    partitioner,
    gpu_name="MI300X"
)
```

### 3. Updated ModelScheduler

ModelScheduler now supports auto-detection:

```python
from model_scheduler import ModelScheduler

# Auto-detect hardware and create partitioner
scheduler = ModelScheduler(
    gpu_id=0,
    auto_detect=True  # Automatically detects hardware
)

# Schedule models (works with both simulation and real)
scheduler.schedule_model(
    "meta-llama/Llama-3.1-8B-Instruct",
    precision="fp16"
)
```

## Capability Levels

### REAL_PARTITIONING
- `amd-smi` is available
- GPU is MI300 series (MI300X, MI325X, MI350X, etc.)
- Uses `ROCmPartitionerReal` with actual partition modes

### SIMULATION
- ROCm or `amd-smi` available but GPU doesn't support partitioning
- Or no GPU detected
- Uses `ROCmPartitioner` (simulation mode)

### NONE
- No GPU hardware detected
- Falls back to simulation mode

## Usage Examples

### Example 1: Auto-Detection (Recommended)

```python
from model_scheduler import ModelScheduler

# Simplest usage - auto-detects everything
scheduler = ModelScheduler(gpu_id=0, auto_detect=True)

# Schedule models
scheduler.schedule_model("meta-llama/Llama-3.1-8B-Instruct")
```

### Example 2: Manual Hardware Detection

```python
from hardware_detector import get_partitioner_class
from model_scheduler import ModelScheduler

# Get appropriate partitioner class
partitioner_class, capability, info = get_partitioner_class(gpu_id=0)

print(f"Capability: {capability.value}")
print(f"GPU Model: {info.model_name}")

# Create partitioner
partitioner = partitioner_class(gpu_id=0)

# Use with scheduler
scheduler = ModelScheduler(partitioner=partitioner)
```

### Example 3: Force Simulation Mode

```python
from auto_partitioner import create_partitioner

# Force simulation even if hardware is available
partitioner = create_partitioner(
    gpu_id=0,
    force_simulation=True
)
```

## Integration with Real Hardware

When real hardware is detected:

1. **Hardware Detection**:
   - Checks for `amd-smi`
   - Detects GPU model
   - Verifies MI300 series

2. **Partitioner Creation**:
   - Creates `ROCmPartitionerReal`
   - Initializes with CPX/NPS4 mode (8 partitions, ~48GB each)

3. **Model Scheduling**:
   - Works the same way as simulation
   - Uses actual logical devices
   - Sets proper environment variables

4. **Environment Variables**:
   ```python
   env_vars = scheduler.get_partition_environment(partition_id=0)
   # Returns:
   # {
   #   'ROCR_VISIBLE_DEVICES': '0',  # Logical device ID
   #   'AIM_PARTITION_ID': '0',
   #   'AIM_COMPUTE_MODE': 'CPX',
   #   'AIM_MEMORY_MODE': 'NPS4',
   #   'AIM_XCD_ID': '0'
   # }
   ```

## Testing

### On Development Machine (No GPU)

```python
# Automatically uses simulation mode
scheduler = ModelScheduler(gpu_id=0, auto_detect=True)
# Works fine for development/testing
```

### On Physical Hardware

```python
# Automatically detects and uses real partitioner
scheduler = ModelScheduler(gpu_id=0, auto_detect=True)
# Uses actual amd-smi commands and partition modes
```

## Verification

Check what mode is being used:

```python
from hardware_detector import HardwareDetector

detector = HardwareDetector()
capability = detector.get_capability(gpu_id=0)

if capability == HardwareCapability.REAL_PARTITIONING:
    print("Using real hardware partitioning")
elif capability == HardwareCapability.SIMULATION:
    print("Using simulation mode")
else:
    print("No hardware detected")
```

## Benefits

1. **Seamless Development**: Works on machines without GPU
2. **Automatic Optimization**: Uses real partitioning when available
3. **No Code Changes**: Same API works everywhere
4. **Production Ready**: Automatically uses real hardware in production

## Migration

Existing code continues to work:

```python
# Old way (still works)
from rocm_partitioner import ROCmPartitioner
partitioner = ROCmPartitioner(gpu_id=0)
scheduler = ModelScheduler(partitioner=partitioner)

# New way (auto-detects)
scheduler = ModelScheduler(gpu_id=0, auto_detect=True)
```

## Troubleshooting

### "amd-smi not available"
- Install ROCm
- Verify: `which amd-smi`
- Check: `amd-smi --version`

### "No GPU detected"
- Check GPU is visible: `amd-smi -l`
- Verify GPU ID is correct
- Check permissions

### "Partitioning not supported"
- Verify GPU is MI300 series
- Check: `amd-smi query --compute-partition`
- May need to use simulation mode

## Next Steps

1. **Test on Physical Hardware**: Validate real partitioning works
2. **Add Monitoring**: Track which mode is being used
3. **Performance Metrics**: Compare simulation vs real
4. **Documentation**: Update deployment guides

