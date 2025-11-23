# Testing Web Application in Kubernetes

## Current Status

**Web app is currently running on the host**, not in Kubernetes. This guide shows how to deploy and test it in Kubernetes.

## Prerequisites

1. ✅ vLLM model deployed to Kubernetes (or use existing Docker container)
2. ✅ Kubernetes cluster accessible
3. ✅ kubectl configured

## Step-by-Step Deployment and Testing

### Step 1: Deploy vLLM Model to Kubernetes (if not already deployed)

```bash
cd /root/AIM_Next/aim-gpu-sharing
./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct
```

**OR** if you're using the Docker container (port 8001), you can:
- Keep using Docker container and update web app endpoint
- Or deploy to Kubernetes for full K8s integration

### Step 2: Verify vLLM Service Exists

```bash
kubectl get svc -n aim-gpu-sharing vllm-model-service
```

Expected output:
```
NAME                 TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
vllm-model-service   NodePort   10.96.x.x       <none>        8000:30080/TCP   ...
```

### Step 3: Deploy Web Application

```bash
cd /root/AIM_Next/aim-gpu-sharing
./k8s/deployment/deploy-web-app.sh
```

This will:
- Create web app deployment
- Create NodePort service on port 30050
- Connect to vLLM via Kubernetes DNS

### Step 4: Verify Deployment

```bash
# Check pods
kubectl get pods -n aim-gpu-sharing

# Check services
kubectl get svc -n aim-gpu-sharing

# View web app logs
kubectl logs -n aim-gpu-sharing -l app=web-app --tail=50
```

### Step 5: Test Access

**Option A: Port Forwarding (Recommended)**
```bash
kubectl port-forward -n aim-gpu-sharing svc/web-app-service 5000:5000
```

Then open browser: `http://localhost:5000`

**Option B: Direct NodePort Access**
```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Access web UI
echo "Web UI: http://${NODE_IP}:30050"
```

### Step 6: Test Chat Functionality

1. Open the web UI
2. Type a message in the chat
3. Verify you get a response from the Qwen model

## Testing Checklist

- [ ] vLLM model pod is running
- [ ] vLLM service is accessible
- [ ] Web app pod is running
- [ ] Web app service is accessible
- [ ] Web UI loads in browser
- [ ] Chat sends messages
- [ ] Chat receives responses from model

## Troubleshooting

### Web App Can't Connect to vLLM

```bash
# Test connectivity from web app pod
kubectl exec -n aim-gpu-sharing -l app=web-app -- \
  curl -s http://vllm-model-service:8000/v1/models

# Check if vLLM service exists
kubectl get svc -n aim-gpu-sharing vllm-model-service

# Check vLLM pod logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model --tail=50
```

### Web App Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n aim-gpu-sharing -l app=web-app

# Check events
kubectl get events -n aim-gpu-sharing --sort-by='.lastTimestamp' | tail -20
```

### Update vLLM Endpoint

If vLLM is running outside Kubernetes (Docker on port 8001):

```bash
# Update web app to use external endpoint
kubectl set env deployment/web-app-deployment -n aim-gpu-sharing \
  VLLM_ENDPOINT=http://<node-ip>:8001/v1

# Restart deployment
kubectl rollout restart deployment/web-app-deployment -n aim-gpu-sharing
```

## Comparison: Host vs Kubernetes

| Aspect | Host (Current) | Kubernetes (New) |
|--------|----------------|------------------|
| **Location** | Direct process | Pod in cluster |
| **Port** | 5000 (direct) | 30050 (NodePort) |
| **Scaling** | Manual | Automatic |
| **Service Discovery** | localhost | DNS (vllm-model-service) |
| **Resource Management** | None | CPU/Memory limits |
| **High Availability** | Single instance | Can have replicas |

## Next Steps After Testing

1. Configure horizontal pod autoscaling
2. Add ingress for external access
3. Set up monitoring and logging
4. Configure resource limits based on usage
5. Add health checks and readiness probes

