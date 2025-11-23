# Deploy vLLM Model - Quick Guide

## Current Situation
- Port 8000 is currently used by a Jupyter/ROCm container
- No vLLM model server is running
- Web app is trying to connect to http://localhost:8000/v1 but there's no vLLM endpoint

## Solution Options

### Option 1: Use Different Port for vLLM (Recommended)

**Step 1: Build the container (if not already built)**
```bash
cd /root/AIM_Next/aim-gpu-sharing
./docker/build-vllm-container.sh
```

**Step 2: Run vLLM on a different port (e.g., 8001)**
```bash
docker run -d --name vllm-server \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  -p 8001:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  aim-gpu-sharing-vllm:latest \
  python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

**Step 3: Update web app to use port 8001**
```bash
# Stop current web app (Ctrl+C)
# Restart with new endpoint
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

### Option 2: Stop Jupyter Container and Use Port 8000

**Step 1: Stop the Jupyter container**
```bash
docker stop rocm
# Or if you need it, change its port mapping
```

**Step 2: Deploy vLLM on port 8000**
```bash
cd /root/AIM_Next/aim-gpu-sharing
./docker/build-vllm-container.sh

docker run -d --name vllm-server \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  -p 8000:8000 \
  -v $(pwd)/model-cache:/workspace/model-cache \
  aim-gpu-sharing-vllm:latest \
  python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

**Step 3: Wait for model to load (may take several minutes)**
```bash
docker logs -f vllm-server
# Wait until you see "Uvicorn running on http://0.0.0.0:8000"
```

**Step 4: Test the endpoint**
```bash
curl http://localhost:8000/v1/models
```

### Option 3: Deploy to Kubernetes

```bash
cd /root/AIM_Next/aim-gpu-sharing
./k8s/deployment/deploy-model.sh meta-llama/Llama-3.1-8B-Instruct
```

Then update web app endpoint to point to the Kubernetes service.

## Verify Model is Running

```bash
# Check container status
docker ps | grep vllm

# Check logs
docker logs vllm-server

# Test endpoint
curl http://localhost:8001/v1/models
# or
curl http://localhost:8000/v1/models
```

## Common Issues

1. **Model download takes time** - First run downloads the model from HuggingFace
2. **GPU memory** - Make sure you have enough GPU memory for the model
3. **Port conflicts** - Use different ports if 8000 is busy
