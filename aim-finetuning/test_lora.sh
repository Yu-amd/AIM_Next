#!/bin/bash
# Test script for LoRA fine-tuning trainer

set -e

echo "=== AIM Fine-Tuning - LoRA Trainer Test ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')" || { echo "Error: PyTorch not installed"; exit 1; }
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')" || { echo "Error: Transformers not installed"; exit 1; }
python3 -c "import peft; print(f'PEFT: {peft.__version__}')" || { echo "Error: PEFT not installed"; exit 1; }
python3 -c "import datasets; print(f'Datasets: {datasets.__version__}')" || { echo "Error: Datasets not installed"; exit 1; }

echo ""
echo "✓ Prerequisites check passed"
echo ""

# Set up test environment
TEST_DIR="./test_output"
DATASET_PATH="./templates/example_dataset.jsonl"
MODEL_ID="Qwen/Qwen2.5-7B-Instruct"

# Check if dataset exists
if [ ! -f "$DATASET_PATH" ]; then
    echo "Error: Dataset file not found: $DATASET_PATH"
    exit 1
fi

echo "Test Configuration:"
echo "  Model: $MODEL_ID"
echo "  Dataset: $DATASET_PATH"
echo "  Output: $TEST_DIR"
echo ""

# Clean up previous test output
if [ -d "$TEST_DIR" ]; then
    echo "Cleaning up previous test output..."
    rm -rf "$TEST_DIR"
fi

mkdir -p "$TEST_DIR"

# Run training
echo "Starting LoRA fine-tuning test..."
echo ""

python3 -m finetuning.base.app \
    --model-id "$MODEL_ID" \
    --dataset-path "$DATASET_PATH" \
    --output-dir "$TEST_DIR" \
    --method lora \
    --learning-rate 2e-4 \
    --batch-size 1 \
    --epochs 1 \
    --max-seq-length 512 \
    --lora-rank 8 \
    --lora-alpha 16

echo ""
echo "=== Test Results ==="

# Check if output directory was created
if [ -d "$TEST_DIR" ]; then
    echo "✓ Output directory created: $TEST_DIR"
    
    # Check for model files
    if [ -f "$TEST_DIR/config.json" ] || [ -f "$TEST_DIR/adapter_config.json" ]; then
        echo "✓ Model files found"
    fi
    
    # Check for training info
    if [ -f "$TEST_DIR/training_info.json" ]; then
        echo "✓ Training info saved"
        echo ""
        echo "Training Info:"
        cat "$TEST_DIR/training_info.json" | python3 -m json.tool 2>/dev/null || cat "$TEST_DIR/training_info.json"
    fi
    
    echo ""
    echo "Test completed successfully!"
    echo ""
    echo "Output files:"
    ls -lh "$TEST_DIR" | head -10
else
    echo "✗ Error: Output directory not created"
    exit 1
fi

