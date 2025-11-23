# Populating Model Sizing Configuration

This guide explains how to populate the `model_sizing_config.yaml` file with model sizing data from the PDF document.

## Model Sizing Tables Location

The model sizing tables are located in the PDF document:
- **Page 14**: Cohere and DeepSeek models (Appendix [1])
- **Page 15**: Gemma, Llama, Mistral, Odia, Qwen, TinyLlama, and Unsloth models (Appendices [2][3][4])

## Method 1: Using the Helper Script

Use the `add_model_size.py` script to add models programmatically:

```bash
# Example: Add a Cohere model
python3 add_model_size.py \
  --model "cohere/Command-R" \
  --params "7B" \
  --memory 16.0 \
  --recommended-partition 20.0

# Example: Add a DeepSeek model
python3 add_model_size.py \
  --model "deepseek-ai/DeepSeek-V2" \
  --params "7B" \
  --memory 14.0
```

## Method 2: Manual YAML Editing

Edit `model_sizing_config.yaml` directly and add entries under the `models:` section:

```yaml
models:
  "cohere/Command-R":
    model_id: "cohere/Command-R"
    parameters: "7B"
    memory_gb: 16.0
    quantization: ["fp16", "int8", "int4"]
    recommended_partition_gb: 20.0
  
  "deepseek-ai/DeepSeek-V2":
    model_id: "deepseek-ai/DeepSeek-V2"
    parameters: "7B"
    memory_gb: 14.0
    quantization: ["fp16", "int8", "int4"]
    recommended_partition_gb: 17.5
```

## Required Information

For each model, you need:

1. **model_id**: Full HuggingFace model identifier (e.g., `"cohere/Command-R"`)
2. **parameters**: Parameter count as string (e.g., `"7B"`, `"13B"`, `"70B"`)
3. **memory_gb**: Minimum GPU memory required in GB (float)
4. **quantization**: List of supported quantization levels (default: `["fp16", "int8", "int4"]`)
5. **recommended_partition_gb**: Recommended partition size in GB (default: memory_gb * 1.25)

## Memory Calculation Guidelines

Memory requirements should include:
- **Model weights**: Parameters × bytes_per_parameter
  - FP16: 2 bytes per parameter
  - INT8: 1 byte per parameter
  - INT4: 0.5 bytes per parameter
- **KV cache**: Typically 20-30% of model size for inference
- **Activations**: Temporary memory during forward pass
- **System overhead**: ~2-4GB for ROCm runtime

**Example calculation for 7B model (FP16):**
- Model weights: 7B × 2 bytes = 14GB
- KV cache (25%): 3.5GB
- Activations: ~1GB
- System overhead: 2GB
- **Total: ~20.5GB** (round to 21GB)

## Model Families to Add

Based on the PDF, add models from these families:

### Page 14 (Appendix [1])
- **Cohere models**: Command-R, Command-R+, etc.
- **DeepSeek models**: DeepSeek-V2, DeepSeek-Coder, etc.

### Page 15 (Appendices [2][3][4])
- **Gemma models**: gemma-2b, gemma-7b, etc.
- **Llama models**: Llama-3.1-8B, Llama-3.1-70B, etc.
- **Mistral models**: Mistral-7B, Mixtral-8x7B, etc.
- **Odia models**: (check PDF for specific models)
- **Qwen models**: Qwen-7B, Qwen-14B, Qwen-72B, etc.
- **TinyLlama models**: TinyLlama-1.1B, etc.
- **Unsloth models**: (check PDF for specific models)

## Validation

After adding models, validate the configuration:

```python
from model_sizing import ModelSizingConfig

config = ModelSizingConfig()
print(f"Loaded {len(config.models)} models")

# Test model lookup
model_info = config.get_model_size("cohere/Command-R")
if model_info:
    print(f"Found: {model_info.model_id} - {model_info.memory_gb}GB")
```

## Quick Reference: Common Model Sizes

Here are approximate memory requirements for common model sizes (FP16, with KV cache):

| Parameters | Approx. Memory (GB) | Recommended Partition (GB) |
|------------|---------------------|----------------------------|
| 1B         | 3-4                 | 5                           |
| 3B         | 7-8                 | 10                          |
| 7B         | 14-16               | 20                          |
| 13B        | 26-30               | 35                          |
| 30B        | 60-70               | 80                          |
| 70B        | 140-160              | 180                         |

*Note: These are estimates. Use actual values from the PDF tables.*

