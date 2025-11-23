#!/bin/bash
# Simplified version without group-add (may work if groups cause issues)

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

# Run vLLM server without group-add (simpler, may still work)
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

echo ""
echo "Container started. Check logs with:"
echo "  docker logs -f vllm-server"
echo ""
echo "Test endpoint with:"
echo "  curl http://localhost:${PORT}/v1/models"
