#!/bin/bash
# Quick script to run Qwen model with vLLM

MODEL="${1:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${2:-8001}"

echo "Starting vLLM server with model: $MODEL"
echo "Port: $PORT"
echo ""

# Check if container already exists
if docker ps -a | grep -q vllm-server; then
    echo "Stopping existing vllm-server container..."
    docker stop vllm-server 2>/dev/null
    docker rm vllm-server 2>/dev/null
fi

# Try with group-add first, fallback to without if it fails
# Note: Some systems don't support --group-add properly
GROUP_ARGS=""
if getent group video > /dev/null 2>&1 && getent group render > /dev/null 2>&1; then
    GROUP_ARGS="--group-add=video --group-add=render"
fi

# Run vLLM server
echo "Starting container..."
if docker run -d --name vllm-server \
  --device=/dev/kfd \
  --device=/dev/dri \
  ${GROUP_ARGS} \
  -p ${PORT}:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
  python3 -m vllm.entrypoints.openai.api_server \
    --model ${MODEL} \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.95 2>&1 | grep -q "Error"; then
    
    echo "Group-add failed, trying without groups..."
    docker rm vllm-server 2>/dev/null
    docker run -d --name vllm-server \
      --device=/dev/kfd \
      --device=/dev/dri \
      -p ${PORT}:8000 \
      -v $(pwd)/model-cache:/workspace/model-cache \
      rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250915 \
      python3 -m vllm.entrypoints.openai.api_server \
        --model ${MODEL} \
        --host 0.0.0.0 \
        --port 8000 \
        --gpu-memory-utilization 0.95
fi

echo ""
echo "Container started. Check logs with:"
echo "  docker logs -f vllm-server"
echo ""
echo "Test endpoint with:"
echo "  curl http://localhost:${PORT}/v1/models"
echo ""
echo "Once ready, update web app:"
echo "  python3 examples/web/web_app.py --endpoint http://localhost:${PORT}/v1 --port 5000 --host 0.0.0.0"
