# Kubernetes Pod Workload Commands

## Quick Commands

### Check Pods in Namespace
```bash
# Basic list
kubectl get pods -n aim-gpu-sharing

# With details (node, IP)
kubectl get pods -n aim-gpu-sharing -o wide

# All resources
kubectl get all -n aim-gpu-sharing
```

### Check All Namespaces
```bash
kubectl get pods --all-namespaces
```

### Resource Usage
```bash
# CPU and memory usage (requires metrics server)
kubectl top pods -n aim-gpu-sharing

# Node resource usage
kubectl top nodes
```

### Detailed Information
```bash
# Describe a specific pod
kubectl describe pod <pod-name> -n aim-gpu-sharing

# Describe all pods with label
kubectl describe pod -n aim-gpu-sharing -l app=vllm-model
```

### View Logs
```bash
# Current logs
kubectl logs <pod-name> -n aim-gpu-sharing

# Follow logs
kubectl logs -f <pod-name> -n aim-gpu-sharing

# Logs from all pods with label
kubectl logs -n aim-gpu-sharing -l app=vllm-model

# Previous container logs (if restarted)
kubectl logs <pod-name> -n aim-gpu-sharing --previous
```

### Watch Pods (Real-time)
```bash
# Watch pods in namespace
kubectl get pods -n aim-gpu-sharing -w

# Watch all namespaces
kubectl get pods --all-namespaces -w
```

### Resource Requests and Limits
```bash
# Show resource requests/limits
kubectl get pod <pod-name> -n aim-gpu-sharing -o jsonpath='{.spec.containers[*].resources}'

# Pretty format
kubectl get pod <pod-name> -n aim-gpu-sharing -o json | jq '.spec.containers[].resources'
```

### Pod Status
```bash
# Status summary
kubectl get pods -n aim-gpu-sharing -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount

# JSON format
kubectl get pods -n aim-gpu-sharing -o json | jq '.items[] | {name: .metadata.name, status: .status.phase, ready: .status.containerStatuses[0].ready}'
```

## Using the Check Script

```bash
# Check pods in aim-gpu-sharing namespace
./k8s/deployment/check-pods.sh

# Check pods in different namespace
./k8s/deployment/check-pods.sh kube-system
```

## Common Status Meanings

- **Pending**: Pod is being scheduled or waiting for resources
- **ContainerCreating**: Container is being created
- **Running**: Pod is running
- **Succeeded**: Pod completed successfully
- **Failed**: Pod failed
- **CrashLoopBackOff**: Pod is crashing and restarting
- **ImagePullBackOff**: Cannot pull container image
- **ErrImagePull**: Error pulling image

## Filtering and Searching

```bash
# Pods by label
kubectl get pods -n aim-gpu-sharing -l app=vllm-model

# Pods by node
kubectl get pods -n aim-gpu-sharing --field-selector spec.nodeName=<node-name>

# Pods by status
kubectl get pods -n aim-gpu-sharing --field-selector status.phase=Running
```

## Resource Information

```bash
# Node resources
kubectl describe node <node-name>

# Allocated resources on node
kubectl describe node <node-name> | grep -A 10 "Allocated resources"

# Pod resource requests
kubectl get pod <pod-name> -n aim-gpu-sharing -o yaml | grep -A 10 resources
```

## Events

```bash
# Recent events in namespace
kubectl get events -n aim-gpu-sharing --sort-by='.lastTimestamp' | tail -20

# Events for specific pod
kubectl get events -n aim-gpu-sharing --field-selector involvedObject.name=<pod-name>
```
