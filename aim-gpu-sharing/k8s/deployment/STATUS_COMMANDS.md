# Checking Deployment Status

## Quick Status Check

```bash
# Run the status check script
./k8s/deployment/check-status.sh
```

## Manual Status Checks

### 1. Check Pod Status
```bash
kubectl get pods -n aim-gpu-sharing
```

**Status meanings:**
- `Pending` - Pod is being scheduled or waiting for resources
- `ContainerCreating` - Container is being created
- `Running` - Pod is running
- `Error` / `CrashLoopBackOff` - Pod has issues

### 2. Check Deployment Status
```bash
kubectl get deployment -n aim-gpu-sharing
```

Look for:
- `READY` column shows `1/1` when ready
- `AVAILABLE` shows number of available replicas

### 3. Detailed Pod Information
```bash
# For web app
kubectl describe pod -n aim-gpu-sharing -l app=web-app

# For vLLM model
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model
```

This shows:
- Events (what's happening)
- Container status
- Resource requests/limits
- Node assignment

### 4. View Pod Logs
```bash
# Web app logs
kubectl logs -n aim-gpu-sharing -l app=web-app --tail=50

# vLLM model logs
kubectl logs -n aim-gpu-sharing -l app=vllm-model --tail=50

# Follow logs in real-time
kubectl logs -n aim-gpu-sharing -l app=web-app -f
```

### 5. Check Events
```bash
kubectl get events -n aim-gpu-sharing --sort-by='.lastTimestamp' | tail -20
```

Shows recent events like:
- Pod creation
- Image pulling
- Container start
- Errors

### 6. Watch Pods (Real-time)
```bash
kubectl get pods -n aim-gpu-sharing -w
```

Press Ctrl+C to stop watching.

## Common Issues and Solutions

### Pod Stuck in "Pending"
```bash
# Check why it's pending
kubectl describe pod -n aim-gpu-sharing <pod-name>

# Common reasons:
# - Insufficient resources (CPU/memory)
# - No nodes available
# - Node selector not matching
```

### Pod Stuck in "ContainerCreating"
```bash
# Check events
kubectl describe pod -n aim-gpu-sharing <pod-name>

# Common reasons:
# - Image pull issues
# - Volume mount problems
# - Resource constraints
```

### Pod in "CrashLoopBackOff"
```bash
# Check logs
kubectl logs -n aim-gpu-sharing <pod-name> --previous

# Check events
kubectl describe pod -n aim-gpu-sharing <pod-name>
```

### Deployment Not Ready
```bash
# Check deployment status
kubectl describe deployment -n aim-gpu-sharing web-app-deployment

# Check replica set
kubectl get rs -n aim-gpu-sharing
```

## Quick Troubleshooting Commands

```bash
# All-in-one status
kubectl get all -n aim-gpu-sharing

# Check if service endpoints exist
kubectl get endpoints -n aim-gpu-sharing

# Check resource usage
kubectl top pods -n aim-gpu-sharing 2>/dev/null || echo "Metrics server not available"

# Check node resources
kubectl describe nodes | grep -A 10 "Allocated resources"
```

## Waiting for Deployment

If deployment script is waiting, you can:

1. **Open another terminal** and run status checks
2. **Check logs** to see what's happening
3. **Cancel and investigate** if stuck too long (Ctrl+C)

The deployment script waits up to 120 seconds for pods to become ready.
