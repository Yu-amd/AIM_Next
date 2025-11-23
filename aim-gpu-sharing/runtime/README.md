# GPU Sharing Runtime Components

This directory contains the core runtime components for GPU memory partitioning and multi-model deployment.

## Components

### `model_sizing.py`
Provides utilities for determining model memory requirements and validating model compatibility with GPU partitions.

**Key Classes:**
- `ModelSizingConfig`: Manages model sizing configuration
- `ModelSizeInfo`: Information about a model's memory requirements

### `rocm_partitioner.py` (Simulation Mode)
⚠️ **Development/Testing Only** - Simulation implementation for testing without hardware.

### `rocm_partitioner_real.py` (Production)
✅ **Real Hardware Implementation** - Uses actual `amd-smi` commands and ROCm partition modes.

**Key Classes:**
- `ROCmPartitionerReal`: Real partitioner using MI300 partition modes
- `ComputePartitionMode`: SPX, CPX, TPX modes
- `MemoryPartitionMode`: NPS1, NPS4 modes
- `MemoryPartition`: Represents a GPU memory partition

**See [ROCM_PARTITIONING.md](./ROCM_PARTITIONING.md) for implementation details.**

### `model_scheduler.py`
Scheduler for managing multiple model instances on a partitioned GPU.

**Key Classes:**
- `ModelScheduler`: Main scheduler class
- `ModelInstance`: Represents a model instance
- `ModelStatus`: Model deployment status enum

### `resource_isolator.py`
Resource isolator for GPU compute isolation to prevent resource monopolization.

**Key Classes:**
- `ResourceIsolator`: Main isolator class
- `ComputeLimits`: Compute resource limits for a partition

## Configuration

### Model Sizing Configuration

The `model_sizing_config.yaml` file contains memory requirements for different models. This file needs to be populated with model sizes from the PDF document.

**To populate the configuration:**

1. Refer to the model sizing tables in the PDF (Appendices [1][2][3][4])
2. For each model, add an entry with:
   - `model_id`: HuggingFace model identifier
   - `parameters`: Parameter count (e.g., "7B", "13B")
   - `memory_gb`: Minimum GPU memory required in GB
   - `quantization`: Supported quantization levels
   - `recommended_partition_gb`: Recommended partition size

**Example entry:**
```yaml
models:
  "meta-llama/Llama-3.1-8B-Instruct":
    model_id: "meta-llama/Llama-3.1-8B-Instruct"
    parameters: "8B"
    memory_gb: 16.0
    quantization: ["fp16", "int8", "int4"]
    recommended_partition_gb: 20.0
```

## Usage

See `example_usage.py` for examples of how to use these components.

### Basic Example

```python
from model_sizing import ModelSizingConfig
from rocm_partitioner import ROCmPartitioner
from model_scheduler import ModelScheduler, ModelStatus

# Initialize partitioner
partitioner = ROCmPartitioner(gpu_id=0)
partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])

# Create scheduler
scheduler = ModelScheduler(partitioner)

# Schedule a model
success, partition_id, error = scheduler.schedule_model(
    "meta-llama/Llama-3.1-8B-Instruct"
)
```

## GPU Specifications

The configuration includes specifications for:
- MI300X: 192GB memory, 304 compute units
- MI325X: 192GB memory, 304 compute units
- MI350X: 192GB memory, 304 compute units
- MI355X: 192GB memory, 304 compute units
- MI350P: 128GB memory, 256 compute units

## Next Steps

1. **Populate model sizes**: Add model sizing data from the PDF to `model_sizing_config.yaml`
2. **Test partitioning**: Run `example_usage.py` to test the partitioning logic
3. **Integration**: Integrate with vLLM and KServe for actual deployment

