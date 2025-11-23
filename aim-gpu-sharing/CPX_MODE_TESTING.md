# CPX Mode Testing Guide

## Overview

CPX (Core Partitioned X-celerator) mode is available on MI300X hardware and provides **8 logical partitions** (one per XCD), which is ideal for multi-model deployment and testing. However, CPX mode typically needs to be configured at boot time.

## CPX Mode Configuration

### Current Status

CPX mode is **available** on MI300X hardware (profile index 3), but **cannot be set programmatically** via `amd-smi set` in the current environment. This is expected behavior - partition modes are typically configured at boot time.

### Checking CPX Mode Availability

```bash
# Check available partition profiles
amd-smi partition -a -g 0

# Check current partition mode
amd-smi partition -c -g 0
```

You should see CPX listed as profile index 3 with 8 partitions.

### Setting CPX Mode

CPX mode can be set via:

1. **Boot-time configuration** (recommended for production)
   - Kernel parameters
   - BIOS/UEFI settings
   - System configuration files

2. **Runtime configuration** (may require root privileges and GPU reset)
   - Special tools/APIs (not available via standard `amd-smi set` command)
   - May require GPU to be in specific state (no active workloads)

## Testing with CPX Mode

### Automatic Detection

The test suite automatically:
1. **Tries to use CPX mode** if `PREFER_CPX=true` (default)
2. **Falls back to current mode** (SPX) if CPX cannot be set
3. **Adapts tests** to work with both 1 partition (SPX) and 8 partitions (CPX)

### Current Behavior

When CPX mode is not set:
- Tests use **SPX mode** (1 partition, 192GB)
- All tests pass with SPX configuration
- Tests are designed to work with both modes

When CPX mode is already set:
- Tests automatically detect and use **CPX mode** (8 partitions, ~48GB each with NPS4)
- Tests validate 8-partition configuration
- Better coverage for multi-partition scenarios

### Running Tests with CPX Preference

```bash
# Default: tries CPX, falls back to current mode
pytest tests/test_rocm_partitioner.py -v

# Explicitly prefer CPX (default behavior)
PREFER_CPX=true pytest tests/test_rocm_partitioner.py -v

# Disable CPX preference (use current mode only)
PREFER_CPX=false pytest tests/test_rocm_partitioner.py -v
```

## CPX Mode Benefits for Testing

### SPX Mode (Current)
- **1 partition** with 192GB
- Good for single large model
- Limited multi-model testing

### CPX Mode (Preferred for Testing)
- **8 partitions** with **24GB each** (192GB / 8)
  - NPS4: 4 quadrants of 48GB each, but each XCD gets 24GB (2 XCDs share each quadrant)
  - NPS1: All XCDs see full memory, but each XCD still gets 24GB share
- Better for multi-model deployment testing
- Tests partition isolation
- Validates multi-partition scheduling
- More realistic production scenarios

## Test Adaptations

The tests automatically adapt to the partition configuration:

### Partition Count
- **SPX**: Expects 1 partition
- **CPX**: Expects 8 partitions

### Memory Per Partition
- **SPX + NPS1**: 192GB per partition (1 partition, full memory)
- **CPX + NPS4**: 24GB per partition (8 partitions, 192GB / 8)
  - Note: NPS4 creates 4 quadrants of 48GB, but each XCD gets 24GB (2 XCDs per quadrant)
- **CPX + NPS1**: 24GB per partition (8 partitions, 192GB / 8)
  - Note: All XCDs see full memory, but each XCD still gets 24GB share

### Test Examples

```python
# Test automatically adapts to partition count
def test_get_available_partitions(self, partitioner):
    available = partitioner.get_available_partitions()
    
    if self._is_real_partitioner(partitioner):
        # Real partitioner: SPX has 1, CPX has 8
        expected_count = len(partitioner.partitions)
        assert len(available) == expected_count
    else:
        # Simulation: configurable
        assert len(available) == 3
```

## Verifying CPX Mode

### In Tests

```python
def test_cpx_mode_availability(self, partitioner):
    if partitioner.compute_mode.value == "CPX":
        assert len(partitioner.partitions) == 8
        # Each partition has XCD ID
        for pid, partition in partitioner.partitions.items():
            assert partition.xcd_id == pid
```

### Manual Verification

```python
from rocm_partitioner_real import ROCmPartitionerReal, ComputePartitionMode

partitioner = ROCmPartitionerReal(gpu_id=0)
compute, memory = partitioner.get_current_partition_mode()

if compute == "CPX":
    print(f"✓ CPX mode active: 8 partitions available")
    partitioner.initialize("MI300X", 
                          ComputePartitionMode.CPX,
                          MemoryPartitionMode.NPS4)
    print(f"  Partitions: {len(partitioner.partitions)}")
    print(f"  Memory per partition: {partitioner.partitions[0].size_bytes/(1024**3):.1f}GB")
else:
    print(f"ℹ Current mode: {compute} (1 partition)")
    print(f"  To use CPX mode, configure at boot time")
```

## Recommendations

### For Development/Testing
1. **Use CPX mode** if available (better test coverage)
2. **Tests work with both modes** (SPX and CPX)
3. **CPX mode preferred** for multi-model scenarios

### For Production
1. **Configure CPX mode at boot time** for multi-model deployment
2. **Use NPS4 memory mode** with CPX for better memory isolation
3. **Test with actual hardware configuration** before deployment

## Environment Variables

- `PREFER_CPX=true`: Try to use CPX mode (default)
- `PREFER_CPX=false`: Use current mode only (don't try CPX)
- `FORCE_SIMULATION=true`: Force simulation mode

## Summary

✅ **CPX mode is available** on MI300X hardware  
✅ **Tests automatically detect and use CPX** when available  
✅ **Tests work with both SPX and CPX** modes  
✅ **CPX mode provides better test coverage** (8 partitions vs 1)  
⚠️ **CPX mode requires boot-time configuration** (cannot be set via amd-smi set)  

The test suite is designed to work optimally with CPX mode when available, while gracefully handling SPX mode when CPX is not configured.

