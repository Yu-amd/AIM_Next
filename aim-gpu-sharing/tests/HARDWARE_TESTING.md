# Hardware Testing Documentation

## Overview

The test suite includes comprehensive hardware verification to ensure that code is running on **real AMD GPU hardware** and not just in simulation mode.

## Hardware Detection

The tests automatically detect and use real hardware when available:

1. **amd-smi Detection**: Tests check for `amd-smi` command availability
2. **Real Partitioner**: Tests use `ROCmPartitionerReal` when hardware is detected
3. **Fallback**: Tests gracefully fall back to simulation if hardware is not available

## Hardware Verification Tests

The `test_hardware_verification.py` suite explicitly verifies:

1. **amd-smi Availability**
   - Checks if `amd-smi` command exists and is executable
   - Required for real hardware operations

2. **Real Hardware Partitioner**
   - Verifies `ROCmPartitionerReal` can be imported and initialized
   - Confirms `amd_smi_available` flag is `True`

3. **Partition Mode Detection**
   - Tests reading current partition modes from hardware
   - Validates SPX/CPX compute modes
   - Validates NPS1/NPS4 memory modes

4. **Partitioner Initialization**
   - Tests initializing partitioner with real hardware
   - Verifies partition creation and sizing
   - Confirms partition count matches hardware configuration

5. **Hardware vs Simulation**
   - Explicitly verifies real hardware is being used
   - Ensures simulation mode is NOT being used

6. **GPU Detection**
   - Tests GPU specification detection
   - Validates memory and compute unit information

## Running Hardware Tests

### Automatic (Recommended)

The test runner automatically includes hardware tests:

```bash
python3 tests/run_all_tests.py
```

This will run:
- Hardware Verification Tests (6 tests)
- ROCm Partitioner Tests (13 tests using real hardware)

### Manual

Run hardware verification tests directly:

```bash
python3 tests/test_hardware_verification.py
```

Run ROCm partitioner tests:

```bash
pytest tests/test_rocm_partitioner.py -v
```

## Expected Results

### On Real Hardware

When running on real hardware with AMD GPU:

```
✓ amd-smi found at: /usr/bin/amd-smi
✓ amd-smi is executable
✓ ROCmPartitionerReal imported successfully
✓ amd-smi available in partitioner
✓ Current compute mode: SPX (or CPX)
✓ Current memory mode: NPS1 (or NPS4)
✓ Partitioner initialized successfully
  - Partitions: 1 (or 4, 8 depending on mode)
  - Partition 0: 192.00 GB (or actual size)
✓ Using real hardware partitioner (not simulation)
```

### Without Hardware

If hardware is not available, tests will:
- Skip hardware-specific tests
- Use simulation mode for partitioner tests
- Provide clear warnings about missing hardware

## Verifying Hardware Usage

To confirm tests are using real hardware:

1. **Check amd-smi availability:**
   ```bash
   which amd-smi
   amd-smi -h
   ```

2. **Run hardware verification:**
   ```bash
   python3 tests/test_hardware_verification.py
   ```

3. **Check test output:**
   - Look for "Using real hardware partitioner (not simulation)"
   - Verify partition counts match hardware configuration
   - Confirm partition sizes match GPU memory

## Hardware Requirements

For hardware tests to pass:

- **AMD GPU** (MI300X, MI350X, or compatible)
- **ROCm drivers** installed
- **amd-smi** command available
- **Sufficient permissions** to access GPU

### Platform-Specific Notes

**Digital Ocean MI300X Instances:**
- ✅ SPX mode fully supported and tested (1 partition, 192GB)
- ⚠️ CPX mode not advertised/available
- ⚠️ Multi-partition tests may be skipped
- ✅ All single-partition functionality fully tested

**Physical Hardware / Other Cloud Providers:**
- Should support both SPX and CPX modes
- CPX mode provides 4 partitions for better multi-model testing
- Full test suite can run without skipping

## Integration with Other Tests

The hardware partitioner is used by:

1. **ROCm Partitioner Tests** - Automatically use real hardware
2. **Model Scheduler Tests** - Use real partitioner when available
3. **Partition Controller** - Uses `ROCmPartitionerReal` in Kubernetes
4. **Metrics Exporter** - Collects metrics from real partitions

## Troubleshooting

### Hardware Not Detected

If hardware tests fail:

1. **Check amd-smi:**
   ```bash
   which amd-smi
   amd-smi -h
   ```

2. **Check GPU visibility:**
   ```bash
   amd-smi -l
   ```

3. **Check ROCm installation:**
   ```bash
   rocm-smi --version
   ```

4. **Check permissions:**
   - Ensure user has access to GPU devices
   - May need to add user to `render` or `video` group

### Force Simulation Mode

To force simulation mode (for testing without hardware):

```bash
FORCE_SIMULATION=true pytest tests/test_rocm_partitioner.py
```

## Test Results

Current hardware test status:

- ✅ **Hardware Verification**: 6/6 tests passing
- ✅ **ROCm Partitioner**: 13/13 tests passing (using real hardware)
- ✅ **Total Hardware Tests**: 19/19 passing

All tests confirm real hardware is being used, not simulation.

