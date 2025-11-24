#!/bin/bash
# Test script for Full fine-tuning trainer

set -e

echo "=== AIM Fine-Tuning - Full Fine-Tuning Test ==="
echo ""
echo "⚠ WARNING: Full fine-tuning requires significant GPU memory!"
echo "   This test uses minimal settings for testing purposes."
echo ""

# Check prerequisites
echo "Checking prerequisites..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')" || { echo "Error: PyTorch not installed"; exit 1; }
python3 -c "import transformers; print(f'Transformers: {transformers.__version__}')" || { echo "Error: Transformers not installed"; exit 1; }
python3 -c "import datasets; print(f'Datasets: {datasets.__version__}')" || { echo "Error: Datasets not installed"; exit 1; }

echo ""
echo "✓ Prerequisites check passed"
echo ""

# Set up test environment
TEST_DIR="./test_output_full"
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
echo "  Method: Full fine-tuning (all parameters trainable)"
echo ""

# Clean up previous test output
if [ -d "$TEST_DIR" ]; then
    echo "Cleaning up previous test output..."
    rm -rf "$TEST_DIR"
fi

mkdir -p "$TEST_DIR"

# Run training
echo "Starting full fine-tuning test..."
echo ""

python3 -m finetuning.base.app \
    --model-id "$MODEL_ID" \
    --dataset-path "$DATASET_PATH" \
    --output-dir "$TEST_DIR" \
    --method full \
    --learning-rate 2e-4 \
    --batch-size 1 \
    --epochs 1 \
    --max-seq-length 512

echo ""
echo "=== Test Results ==="

# Check if output directory was created
if [ -d "$TEST_DIR" ]; then
    echo "✓ Output directory created: $TEST_DIR"
    
    # Check for model files
    if [ -f "$TEST_DIR/config.json" ]; then
        echo "✓ Model files found"
    fi
    
    # Check for AIM profile
    if [ -f "$TEST_DIR/aim_profile.json" ]; then
        echo "✓ AIM profile generated"
        echo ""
        echo "AIM Profile:"
        cat "$TEST_DIR/aim_profile.json" | python3 -m json.tool 2>/dev/null || cat "$TEST_DIR/aim_profile.json"
    else
        echo "⚠ AIM profile not found (may have failed to generate)"
    fi
    
    # Check for training info
    if [ -f "$TEST_DIR/training_info.json" ]; then
        echo ""
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

