# Web Application Kubernetes Deployment Guide

## Overview

This guide shows how to deploy the web application to Kubernetes so it runs in a pod instead of directly on the host.

## Prerequisites

1. Kubernetes cluster with AMD GPU operator
2. vLLM model already deployed (see `deploy-model.sh`)
3. kubectl configured to access the cluster

## Quick Start

### Step 1: Deploy Web Application

```bash
cd /root/AIM_Next/aim-gpu-sharing
./k8s/deployment/deploy-web-app.sh
```

This will:
- Create the web app deployment
- Create a NodePort service on port 30050
- Connect to vLLM service at `http://vllm-model-service:8000/v1`

### Step 2: Access the Web UI

**Option A: Direct Access via NodePort**
```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Access web UI
http://${NODE_IP}:30050
```

**Option B: Port Forwarding (Recommended for Remote Access)**
```bash
kubectl port-forward -n aim-gpu-sharing svc/web-app-service 5000:5000
```

Then open: `http://localhost:5000`

## Custom vLLM Endpoint

If your vLLM service is at a different location:

```bash
./k8s/deployment/deploy-web-app.sh http://your-vllm-service:8000/v1
```

## Verify Deployment

```bash
# Check pods
kubectl get pods -n aim-gpu-sharing -l app=web-app

# Check service
kubectl get svc -n aim-gpu-sharing web-app-service

# View logs
kubectl logs -n aim-gpu-sharing -l app=web-app --tail=50

# Test health endpoint
curl http://localhost:5000/api/health
# (if using port-forward)
```

## Architecture

```
┌─────────────────────────────────┐
│   Web Browser                   │
└────────────┬────────────────────┘
             │
             │ HTTP
             │
┌────────────▼────────────────────┐
│   web-app-service (NodePort)     │
│   Port: 30050                    │
└────────────┬────────────────────┘
             │
             │
┌────────────▼────────────────────┐
│   web-app-deployment (Pod)      │
│   - Flask application            │
│   - Port: 5000                   │
└────────────┬────────────────────┘
             │
             │ HTTP
             │
┌────────────▼────────────────────┐
│   vllm-model-service            │
│   - vLLM API                    │
│   - Port: 8000                  │
└─────────────────────────────────┘
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n aim-gpu-sharing -l app=web-app

# Check logs
kubectl logs -n aim-gpu-sharing -l app=web-app
```

### Cannot Connect to vLLM

```bash
# Check if vLLM service exists
kubectl get svc -n aim-gpu-sharing vllm-model-service

# Test connectivity from web app pod
kubectl exec -n aim-gpu-sharing -l app=web-app -- curl http://vllm-model-service:8000/v1/models
```

### Update vLLM Endpoint

```bash
# Update environment variable
kubectl set env deployment/web-app-deployment -n aim-gpu-sharing \
  VLLM_ENDPOINT=http://new-endpoint:8000/v1

# Restart pods
kubectl rollout restart deployment/web-app-deployment -n aim-gpu-sharing
```

## Cleanup

```bash
# Delete web app deployment
kubectl delete -f k8s/deployment/web-app-deployment.yaml

# Or delete everything in namespace
kubectl delete namespace aim-gpu-sharing
```

## Comparison: Host vs Kubernetes

| Feature | Host Deployment | Kubernetes Deployment |
|---------|----------------|----------------------|
| Location | Direct on host | Pod in cluster |
| Port | 5000 (direct) | 30050 (NodePort) |
| Scaling | Manual | Automatic (replicas) |
| Management | Process manager | Kubernetes |
| Service Discovery | localhost | DNS-based |
| Resource Limits | None | Configurable |

## Next Steps

- Add ingress controller for external access
- Configure horizontal pod autoscaling
- Add monitoring and logging
- Set up SSL/TLS certificates

