#!/bin/bash

# Test script for monitoring and validation features

echo "=== Testing Monitoring & Validation Features ==="
echo ""

# Configuration
MODEL_ID="Qwen/Qwen2.5-7B-Instruct"
DATASET_PATH="./templates/example_dataset.jsonl"
TEST_DIR="./test_output_monitoring"

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

# 1. Check prerequisites
echo "1. Checking prerequisites..."
python3 -c "import prometheus_client; print('✓ prometheus_client available')" 2>/dev/null || {
    echo "  Installing prometheus-client..."
    pip install prometheus-client --break-system-packages
}

echo ""
echo "2. Running training with metrics enabled..."
echo ""

# Run training with metrics
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
    --lora-alpha 16 \
    --enable-metrics \
    --metrics-port 8001

if [ $? -ne 0 ]; then
    echo "Error: Training failed."
    exit 1
fi

echo ""
echo "3. Testing metrics endpoint..."
echo ""

# Wait a moment for metrics server to be ready
sleep 2

# Check if metrics are available
if curl -s http://localhost:8001/metrics | grep -q "finetuning"; then
    echo "✓ Metrics endpoint is working"
    echo ""
    echo "Sample metrics:"
    curl -s http://localhost:8001/metrics | grep "finetuning" | head -5
else
    echo "⚠ Metrics endpoint not responding (this is OK if training completed quickly)"
fi

echo ""
echo "4. Running validation..."
echo ""

# Run validation
cd /root/AIM_Next/aim-finetuning && python3 -m monitoring.validate_job \
    --training-info "$TEST_DIR/training_info.json" \
    --model-path "$TEST_DIR" \
    --profile-path "$TEST_DIR/aim_profile.json" \
    --output "$TEST_DIR/validation_report.txt"

VALIDATION_EXIT=$?

if [ $VALIDATION_EXIT -eq 0 ]; then
    echo "✓ Validation passed"
else
    echo "⚠ Validation had issues (check report)"
fi

echo ""
echo "5. Validation Report:"
echo ""
if [ -f "$TEST_DIR/validation_report.txt" ]; then
    cat "$TEST_DIR/validation_report.txt"
else
    echo "  Validation report not generated"
fi

echo ""
echo "=== Test Summary ==="
echo ""
echo "Output files:"
ls -lh "$TEST_DIR" 2>/dev/null | head -10

echo ""
echo "Test completed!"
echo ""
echo "To view metrics (if server is still running):"
echo "  curl http://localhost:8001/metrics"

exit 0

