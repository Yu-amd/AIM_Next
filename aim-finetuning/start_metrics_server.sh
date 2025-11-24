#!/bin/bash

# Script to start a standalone metrics server for testing

PORT=${1:-8000}
JOB_NAME=${2:-"test-job"}
MODEL_ID=${3:-"Qwen/Qwen2.5-7B-Instruct"}
METHOD=${4:-"lora"}
TRAINING_INFO=${5:-""}

echo "=== Starting Metrics Server ==="
echo ""
echo "Port: $PORT"
echo "Job Name: $JOB_NAME"
echo "Model ID: $MODEL_ID"
echo "Method: $METHOD"
echo ""

# Check if port is already in use
if netstat -tlnp 2>/dev/null | grep -q ":$PORT " || \
   ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "⚠ Port $PORT is already in use!"
    echo "   Use a different port or stop the existing service"
    exit 1
fi

# Start metrics server
echo "Starting metrics server on port $PORT..."
echo "Access metrics at: http://localhost:$PORT/metrics"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd /root/AIM_Next/aim-finetuning

if [ -n "$TRAINING_INFO" ] && [ -f "$TRAINING_INFO" ]; then
    python3 -m monitoring.metrics_server \
        --port "$PORT" \
        --job-name "$JOB_NAME" \
        --model-id "$MODEL_ID" \
        --method "$METHOD" \
        --training-info "$TRAINING_INFO"
else
    python3 -m monitoring.metrics_server \
        --port "$PORT" \
        --job-name "$JOB_NAME" \
        --model-id "$MODEL_ID" \
        --method "$METHOD"
fi

