# AIM Profiles Update - Partition Mode Information

## Summary

All AIM profiles have been updated to include **partition mode information** (SPX/CPX compute modes and NPS1/NPS4 memory modes) reflecting the actual hardware configuration.

## Changes Made

### 1. Updated `AIMProfileGenerator`

**Added partition mode detection:**
- Automatically detects current compute mode (SPX/CPX) from hardware
- Automatically detects current memory mode (NPS1/NPS4) from hardware
- Determines partition count and size based on detected modes
- Falls back to defaults (SPX/NPS1, 1 partition, 192GB) if hardware not available

**Updated profile structure:**
- Added partition mode fields to `gpu_sharing` section
- Added `partition_config` to `metadata` section
- Adjusted `recommended_partition_gb` based on actual partition sizes

### 2. Profile Structure Updates

**Before:**
```json
{
  "gpu_sharing": {
    "enabled": true,
    "memory_limit_gb": 25.0,
    "partition_id": null,
    "qos_priority": "medium"
  }
}
```

**After:**
```json
{
  "gpu_sharing": {
    "enabled": true,
    "memory_limit_gb": 25.0,
    "partition_id": null,
    "qos_priority": "medium",
    "compute_mode": "SPX",
    "memory_mode": "NPS1",
    "partition_count": 1,
    "partition_size_gb": 192.0
  },
  "metadata": {
    "partition_config": {
      "compute_mode": "SPX",
      "memory_mode": "NPS1",
      "partition_count": 1,
      "partition_size_gb": 192.0
    }
  }
}
```

### 3. Regenerated All Profiles

All **114 profile files** have been regenerated with partition mode information:
- ✅ All profiles include `compute_mode` and `memory_mode`
- ✅ All profiles include `partition_count` and `partition_size_gb`
- ✅ All profiles include `partition_config` in metadata
- ✅ Partition recommendations adjusted based on actual partition sizes

## Current Configuration

Based on detected hardware:
- **Compute Mode**: SPX (Single Partition)
- **Memory Mode**: NPS1 (All memory accessible)
- **Partition Count**: 1
- **Partition Size**: 192GB

## CPX Mode Support

When CPX mode is configured:
- Profiles will automatically reflect:
  - **Compute Mode**: CPX
  - **Partition Count**: 8
  - **Partition Size**: ~48GB (with NPS4) or 192GB (with NPS1)
- Profiles will be regenerated with correct CPX information
- `recommended_partition_gb` will be adjusted for smaller partitions

## Usage

### Generating Profiles

```python
from aim_profile_generator import AIMProfileGenerator

# Automatically detects partition modes from hardware
generator = AIMProfileGenerator(gpu_id=0)

# Generate profiles (includes partition mode info)
profiles = generator.generate_all_profiles()

# Save profiles
generator.save_all_profiles("aim_profiles/")
```

### Reading Profile Information

```python
import json

# Load a profile
with open("aim_profiles/meta-llama_Llama-3.1-8B-Instruct-fp16.json") as f:
    profile = json.load(f)

# Get partition mode information
compute_mode = profile["gpu_sharing"]["compute_mode"]
memory_mode = profile["gpu_sharing"]["memory_mode"]
partition_count = profile["gpu_sharing"]["partition_count"]
partition_size = profile["gpu_sharing"]["partition_size_gb"]

print(f"Partition config: {compute_mode}/{memory_mode}")
print(f"Partitions: {partition_count} x {partition_size}GB")
```

## Test Updates

Updated `test_profile_gpu_sharing_config` to verify:
- ✅ `compute_mode` is present and valid (SPX or CPX)
- ✅ `memory_mode` is present and valid (NPS1 or NPS4)
- ✅ `partition_count` matches compute mode (1 for SPX, 8 for CPX)
- ✅ `partition_config` in metadata matches gpu_sharing values

## Benefits

1. **Accurate Configuration**: Profiles reflect actual hardware partition configuration
2. **Better Scheduling**: Scheduler can use partition mode info for optimal placement
3. **CPX Ready**: Automatically adapts when CPX mode is configured
4. **Transparency**: Clear visibility into partition configuration in profiles

## Files Updated

- ✅ `runtime/aim_profile_generator.py` - Added partition mode detection and inclusion
- ✅ `runtime/aim_profiles/*.json` - All 114 profiles regenerated with partition info
- ✅ `tests/test_aim_profile_generator.py` - Updated to verify partition mode fields

## Verification

All profiles verified to include:
```bash
# Check a profile
python3 -c "import json; p=json.load(open('runtime/aim_profiles/meta-llama_Llama-3.1-8B-Instruct-fp16.json')); print('Compute:', p['gpu_sharing']['compute_mode']); print('Memory:', p['gpu_sharing']['memory_mode']); print('Partitions:', p['gpu_sharing']['partition_count'])"
```

## Conclusion

✅ **All AIM profiles updated** with partition mode information  
✅ **Reflects actual hardware configuration** (SPX/NPS1 currently)  
✅ **Automatically adapts to CPX mode** when configured  
✅ **All tests pass** with updated profile structure  
✅ **114 profiles regenerated** with correct partition information  

The profiles now accurately represent the GPU partition configuration and will automatically update when partition modes change.

