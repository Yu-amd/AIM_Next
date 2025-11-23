# AIM Profiles for GPU Sharing

This directory contains AIM profiles for all models with different precision levels (FP16, INT8, INT4).

## Overview

Each model has multiple profile variants, one for each supported quantization level:
- **FP16**: Full precision (baseline)
- **INT8**: 8-bit quantization (~60% of FP16 memory)
- **INT4**: 4-bit quantization (~40% of FP16 memory)

## Profile Structure

Each AIM profile JSON file contains:

```json
{
  "model_id": "meta-llama/Llama-3.1-8B-Instruct",
  "variant_id": "meta-llama/Llama-3.1-8B-Instruct-fp16",
  "version": "1.0.0-fp16",
  "parameters": "8B",
  "precision": "fp16",
  "memory_requirement_gb": 20.0,
  "recommended_partition_gb": 25.0,
  "gpu_sharing": {
    "enabled": true,
    "memory_limit_gb": 25.0,
    "partition_id": null,
    "qos_priority": "medium"
  },
  "resource_requirements": {
    "gpu_memory_gb": 20.0,
    "gpu_count": 1,
    "cpu_cores": 2,
    "system_memory_gb": 16
  },
  "metadata": {
    "quantization": "fp16",
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "parameters": "8B"
  }
}
```

## Profile Naming Convention

Profiles are named using the pattern: `{model_id}-{precision}.json`

Where:
- `model_id` is the HuggingFace model identifier (with `/` replaced by `_`)
- `precision` is one of: `fp16`, `int8`, `int4`

Example: `meta-llama_Llama-3.1-8B-Instruct-fp16.json`

## Usage

### Finding a Profile

To find profiles for a specific model:

```bash
# List all profiles for a model
ls aim_profiles/ | grep "meta-llama_Llama-3.1-8B"

# Output:
# meta-llama_Llama-3.1-8B-Instruct-fp16.json
# meta-llama_Llama-3.1-8B-Instruct-int8.json
# meta-llama_Llama-3.1-8B-Instruct-int4.json
```

### Loading a Profile

```python
import json
from pathlib import Path

profile_path = Path("aim_profiles/meta-llama_Llama-3.1-8B-Instruct-fp16.json")
with open(profile_path) as f:
    profile = json.load(f)

print(f"Model: {profile['model_id']}")
print(f"Precision: {profile['precision']}")
print(f"Memory: {profile['memory_requirement_gb']}GB")
print(f"Recommended partition: {profile['recommended_partition_gb']}GB")
```

### Using with GPU Partitioning

```python
from model_sizing import ModelSizingConfig
from rocm_partitioner import ROCmPartitioner
from model_scheduler import ModelScheduler

# Load profile
import json
with open("aim_profiles/meta-llama_Llama-3.1-8B-Instruct-fp16.json") as f:
    profile = json.load(f)

# Initialize partitioner
partitioner = ROCmPartitioner(gpu_id=0)
partitioner.initialize("MI300X", [40.0, 40.0, 40.0, 40.0])

# Schedule model using profile
scheduler = ModelScheduler(partitioner)
success, partition_id, error = scheduler.schedule_model(
    profile['model_id'],
    priority=10
)

if success:
    print(f"Scheduled {profile['model_id']} on partition {partition_id}")
    print(f"Memory requirement: {profile['memory_requirement_gb']}GB")
```

## Statistics

- **Total Models**: 38
- **Total Profiles**: 114 (3 precision levels × 38 models)
- **Profile Format**: JSON
- **Last Updated**: Generated from model sizing tables

## Model Coverage

Profiles are available for:

- **Cohere**: 2 models (8B, 32B)
- **DeepSeek**: 9 models (1.5B to 70B)
- **Gemma**: 4 models (1B to 27B)
- **Llama**: 6 models (1B to 70B)
- **Mistral**: 3 models (24B to 70B)
- **Odia**: 1 model (7B)
- **Qwen**: 9 models (0.5B to 235B)
- **TinyLlama**: 1 model (1.1B)
- **Unsloth**: 2 models (11B, 30B)

## Regenerating Profiles

To regenerate all profiles after updating model sizing configuration:

```bash
cd aim-gpu-sharing/runtime
python3 generate_aim_profiles.py
```

This will update all profile files in the `aim_profiles/` directory.

## Integration with AIM Deployment

These profiles can be used with:
- **KServe InferenceService CRDs**: Reference profile for resource allocation
- **GPU Partitioning**: Determine optimal partition allocation
- **Model Scheduler**: Validate model fits in available partitions
- **Resource Planning**: Estimate infrastructure requirements

