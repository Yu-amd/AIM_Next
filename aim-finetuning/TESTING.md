# Testing Guide for AIM Fine-Tuning

This document provides instructions for testing the fine-tuning service, specifically the LoRA trainer.

## Prerequisites

### System Requirements
- Python 3.10 or higher
- AMD GPU with ROCm support (or NVIDIA GPU with CUDA)
- At least 16GB GPU memory (for 7B models)
- 20GB+ free disk space (for model downloads and checkpoints)

### Python Dependencies

Install required packages:

```bash
cd aim-finetuning
pip install -r requirements.txt
```

Or install individually:

```bash
pip install torch transformers peft datasets accelerate sentencepiece protobuf
```

### Verify Installation

```bash
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')"
python3 -c "import peft; print(f'PEFT: {peft.__version__}')"
python3 -c "import datasets; print(f'Datasets: {datasets.__version__}')"
```

## Quick Test (Automated)

### LoRA Fine-Tuning

```bash
chmod +x test_lora.sh
./test_lora.sh
```

### QLoRA Fine-Tuning (4-bit Quantization)

```bash
chmod +x test_qlora.sh
./test_qlora.sh
```

**Note:** QLoRA requires `bitsandbytes` package:
```bash
pip install bitsandbytes --break-system-packages
```

### Full Fine-Tuning

```bash
chmod +x test_full.sh
./test_full.sh
```

**Warning:** Full fine-tuning requires significant GPU memory. The test uses minimal settings.

These scripts will:
1. Check prerequisites
2. Use the example dataset from `templates/example_dataset.jsonl`
3. Run a minimal training session (1 epoch, small batch size)
4. Verify output files are created
5. Check for AIM profile generation
6. Display training results

## Manual Testing

### Step 1: Prepare Test Dataset

Create a small test dataset in JSONL format:

```bash
cat > test_dataset.jsonl << EOF
{"instruction": "What is the capital of France?", "output": "The capital of France is Paris."}
{"instruction": "Explain what machine learning is.", "output": "Machine learning is a subset of artificial intelligence."}
{"instruction": "Write a Python function to add two numbers.", "output": "def add(a, b):\n    return a + b"}
EOF
```

Or use the provided example:

```bash
cp templates/example_dataset.jsonl test_dataset.jsonl
```

### Step 2: Run LoRA Training

#### Basic Command

```bash
python3 -m finetuning.base.app \
    --model-id Qwen/Qwen2.5-7B-Instruct \
    --dataset-path test_dataset.jsonl \
    --output-dir ./output \
    --method lora \
    --learning-rate 2e-4 \
    --batch-size 1 \
    --epochs 1 \
    --lora-rank 8 \
    --lora-alpha 16
```

#### With Configuration File

Create a config file:

```json
{
  "model_id": "Qwen/Qwen2.5-7B-Instruct",
  "method": "lora",
  "hyperparameters": {
    "learning_rate": 2e-4,
    "batch_size": 1,
    "epochs": 1,
    "max_seq_length": 512,
    "lora_rank": 8,
    "lora_alpha": 16
  },
  "lora_config": {
    "r": 8,
    "lora_alpha": 16,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "lora_dropout": 0.05
  }
}
```

Run with config:

```bash
python3 -m finetuning.base.app \
    --config config.json \
    --dataset-path test_dataset.jsonl \
    --output-dir ./output
```

### Step 3: Verify Results

After training completes, check the output directory:

```bash
ls -lh output/
```

Expected files:
- `adapter_config.json` - LoRA adapter configuration
- `adapter_model.bin` or `adapter_model.safetensors` - LoRA weights
- `training_info.json` - Training metadata and results
- `checkpoint-*` directories (if multiple checkpoints saved)

View training info:

```bash
cat output/training_info.json | python3 -m json.tool
```

## Testing Different Scenarios

### Small Model Test (Faster)

For quicker testing, use a smaller model:

```bash
python3 -m finetuning.base.app \
    --model-id microsoft/Phi-3-mini-4k-instruct \
    --dataset-path test_dataset.jsonl \
    --output-dir ./output \
    --method lora \
    --batch-size 2 \
    --epochs 1 \
    --lora-rank 4
```

### Custom LoRA Configuration

Test different LoRA parameters:

```bash
python3 -m finetuning.base.app \
    --model-id Qwen/Qwen2.5-7B-Instruct \
    --dataset-path test_dataset.jsonl \
    --output-dir ./output \
    --method lora \
    --lora-rank 32 \
    --lora-alpha 64 \
    --batch-size 1 \
    --epochs 1
```

### Different Dataset Formats

#### CSV Format

```csv
instruction,output
"What is AI?","AI is artificial intelligence."
"Explain ML.","ML is machine learning."
```

The loader will automatically detect CSV format.

#### HuggingFace Dataset

```bash
python3 -m finetuning.base.app \
    --model-id Qwen/Qwen2.5-7B-Instruct \
    --dataset-path "hf://datasets/your-dataset" \
    --output-dir ./output \
    --method lora
```

## Troubleshooting

### Out of Memory (OOM) Errors

If you encounter GPU memory errors:

1. **Reduce batch size:**
   ```bash
   --batch-size 1
   ```

2. **Reduce sequence length:**
   ```bash
   --max-seq-length 512
   ```

3. **Use gradient checkpointing** (enabled by default):
   ```json
   "gradient_checkpointing": true
   ```

4. **Use smaller LoRA rank:**
   ```bash
   --lora-rank 4
   ```

### Model Download Issues

If model download fails:

1. **Set HuggingFace token** (for gated models):
   ```bash
   export HF_TOKEN=your_token_here
   ```

2. **Use local model path:**
   ```bash
   --model-id /path/to/local/model
   ```

### Import Errors

If you get import errors:

1. **Check Python path:**
   ```bash
   export PYTHONPATH=$PWD:$PYTHONPATH
   ```

2. **Install missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Training Hangs or Slow

1. **Check GPU utilization:**
   ```bash
   rocm-smi  # For AMD GPUs
   nvidia-smi  # For NVIDIA GPUs
   ```

2. **Reduce dataset size** for initial testing

3. **Use smaller model** for faster iteration

## Expected Output

Successful training should produce:

```
2024-XX-XX INFO - Loading model: Qwen/Qwen2.5-7B-Instruct
2024-XX-XX INFO - Model and tokenizer loaded successfully
2024-XX-XX INFO - Applying LoRA adapters...
2024-XX-XX INFO - LoRA adapters applied
2024-XX-XX INFO - Starting training...
2024-XX-XX INFO - Training completed
2024-XX-XX INFO - Model saved to ./output
2024-XX-XX INFO - Training info saved to ./output/training_info.json
```

## Validation Checklist
- [ ] Prometheus metrics are exported (if `--enable-metrics` is used).
- [ ] Validation framework checks pass.
- [ ] Validation report is generated correctly.


After running tests, verify:

- [ ] Training completes without errors
- [ ] Output directory is created
- [ ] LoRA adapter files are present (`adapter_config.json`, `adapter_model.*`)
- [ ] `training_info.json` contains training metrics
- [ ] Model can be loaded (test loading the adapter)
- [ ] Training loss decreases (check logs)

## Testing All Methods

### 1. LoRA Fine-Tuning
```bash
./test_lora.sh
```

### 2. QLoRA Fine-Tuning (Memory-Efficient)
```bash
# Install bitsandbytes first
pip install bitsandbytes --break-system-packages
./test_qlora.sh
```

### 3. Full Fine-Tuning
```bash
./test_full.sh
```

### 4. Verify AIM Profile Generation

After any training completes, check for the AIM profile:

```bash
cat test_output*/aim_profile.json | python3 -m json.tool
```

The profile should include:
- Model memory requirements
- Recommended GPU partition size
- Fine-tuning method and configuration
- Training metadata

## Next Steps

After successful testing:

1. **Test with larger datasets** - Use your actual training data
2. **Experiment with hyperparameters** - Tune learning rate, LoRA rank, etc.
3. **Compare methods** - Test LoRA vs QLoRA vs Full fine-tuning
4. **Use AIM profiles** - Use generated profiles for deployment planning
5. **Test on GPU** - Run tests with ROCm/CUDA for better performance

## Performance Benchmarks

For reference, typical training times on MI300X (192GB):

- **Qwen2.5-7B-Instruct** with LoRA (rank=16):
  - Small dataset (100 examples): ~5-10 minutes
  - Medium dataset (1000 examples): ~30-60 minutes
  - Large dataset (10000 examples): ~5-10 hours

Note: Times vary based on sequence length, batch size, and other hyperparameters.

