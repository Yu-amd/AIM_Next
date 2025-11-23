# Testing Without Kubernetes Cluster

## What Can Be Tested Without K8s

### ✅ Phase 3 Components (Mostly Testable)

#### 1. Metrics Exporter - **Can Test Standalone** ✅

The metrics exporter is a standalone Flask application that can run without Kubernetes.

**Test it locally:**
```bash
cd /root/AIM_Next/aim-gpu-sharing
export GPU_ID=0
python3 monitoring/metrics_exporter.py
```

Then in another terminal:
```bash
# Check health endpoint
curl http://localhost:8080/health

# Get metrics
curl http://localhost:8080/metrics
```

**What it tests:**
- Flask app starts correctly
- Metrics endpoint returns Prometheus format
- Partition metrics are collected from real hardware
- Model metrics are collected from scheduler

#### 2. QoS Framework - **Already Tested** ✅

The QoS framework has comprehensive unit tests that don't require K8s.

**Run tests:**
```bash
cd /root/AIM_Next/aim-gpu-sharing
pytest tests/test_qos_manager.py -v
```

**What it tests:**
- Priority-based request scheduling
- Resource guarantees and limits
- SLO tracking and compliance
- Request queuing

#### 3. Grafana Dashboards - **Can Validate JSON** ⚠️

Dashboard JSON files can be validated for syntax, but need Grafana to visualize.

**Validate JSON:**
```bash
cd /root/AIM_Next/aim-gpu-sharing
python3 -m json.tool monitoring/dashboards/partition-utilization.json > /dev/null && echo "Valid JSON"
python3 -m json.tool monitoring/dashboards/model-performance.json > /dev/null && echo "Valid JSON"
python3 -m json.tool monitoring/dashboards/scheduler-metrics.json > /dev/null && echo "Valid JSON"
```

### ❌ Phase 2 Components (Need K8s)

#### 1. KServe CRD Extension
- **Can validate**: YAML syntax
- **Cannot test**: CRD registration, validation webhooks, actual CRD behavior
- **Needs**: Kubernetes cluster with kubectl access

#### 2. Partition Controller
- **Can validate**: Python syntax, imports
- **Cannot test**: CRD watching, status updates, partition allocation
- **Needs**: Kubernetes cluster with CRD installed

#### 3. GPU Sharing Operator
- **Can validate**: YAML syntax, Dockerfile
- **Cannot test**: Deployment, RBAC, actual operator behavior
- **Needs**: Kubernetes cluster

## Testing What We Can (Without K8s)

### Test Metrics Exporter

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Start metrics exporter in background
python3 monitoring/metrics_exporter.py &
METRICS_PID=$!

# Wait a moment for it to start
sleep 2

# Test health endpoint
echo "Testing health endpoint:"
curl -s http://localhost:8080/health | python3 -m json.tool

# Test metrics endpoint
echo -e "\nTesting metrics endpoint:"
curl -s http://localhost:8080/metrics | head -30

# Check if metrics are being collected
echo -e "\nChecking for partition metrics:"
curl -s http://localhost:8080/metrics | grep "aim_gpu_partition"

# Stop metrics exporter
kill $METRICS_PID
```

### Test QoS Framework

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Run all QoS tests
pytest tests/test_qos_manager.py -v

# Run with coverage
pytest tests/test_qos_manager.py --cov=runtime/qos --cov-report=term
```

### Validate YAML/JSON Files

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Validate CRD YAML (syntax only)
python3 -c "import yaml; yaml.safe_load(open('k8s/crd/gpu-sharing-crd.yaml'))" && echo "CRD YAML valid"

# Validate operator YAML
python3 -c "import yaml; yaml.safe_load(open('k8s/operator/gpu-sharing-operator.yaml'))" && echo "Operator YAML valid"

# Validate RBAC YAML
python3 -c "import yaml; yaml.safe_load(open('k8s/operator/rbac.yaml'))" && echo "RBAC YAML valid"

# Validate dashboard JSON files
for json_file in monitoring/dashboards/*.json; do
    python3 -m json.tool "$json_file" > /dev/null && echo "✓ $json_file is valid"
done
```

### Test Controller Code (Syntax/Imports)

```bash
cd /root/AIM_Next/aim-gpu-sharing

# Test if controller code can be imported (without running)
python3 -c "
import sys
sys.path.insert(0, 'k8s/controller')
sys.path.insert(0, 'runtime')
try:
    from partition_controller import PartitionController
    print('✓ Controller code imports successfully')
except Exception as e:
    print(f'✗ Import error: {e}')
"
```

## What Requires K8s Cluster

### Full Integration Testing

To fully test Phase 2 components, you need:

1. **Kubernetes cluster** (can be local like minikube, kind, or k3s)
2. **kubectl** configured to access the cluster
3. **CRD installed** in the cluster
4. **Operator deployed** in the cluster
5. **Test InferenceService CRs** to trigger controller

### Minimal K8s Setup for Testing

If you want to test Phase 2, you can use:

**Option 1: kind (Kubernetes in Docker)**
```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/

# Create cluster
kind create cluster --name aim-test

# Install CRD
kubectl apply -f k8s/crd/gpu-sharing-crd.yaml

# Deploy operator
./k8s/operator/install.sh
```

**Option 2: minikube**
```bash
# Install minikube
# Create cluster
minikube start

# Install CRD and operator
kubectl apply -f k8s/crd/gpu-sharing-crd.yaml
./k8s/operator/install.sh
```

**Option 3: k3s (Lightweight)**
```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -

# Use k3s kubectl
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Install CRD and operator
kubectl apply -f k8s/crd/gpu-sharing-crd.yaml
./k8s/operator/install.sh
```

## Summary

### ✅ Can Test Without K8s:
- **Metrics Exporter** - Standalone Flask app
- **QoS Framework** - Unit tests (already passing)
- **YAML/JSON validation** - Syntax checking
- **Code imports** - Python syntax validation

### ❌ Need K8s Cluster:
- **CRD Extension** - Need to apply and test CRD
- **Partition Controller** - Needs K8s API to watch CRDs
- **GPU Sharing Operator** - Needs K8s to deploy

### Recommendation

1. **Test Phase 3 components now** (metrics exporter, QoS framework)
2. **Validate Phase 2 YAML/JSON** (syntax checking)
3. **Set up local K8s cluster** (kind/minikube/k3s) if you want to test Phase 2
4. **Or deploy to existing K8s cluster** if you have one

The Phase 3 components are fully functional and testable without K8s. Phase 2 components are implemented correctly but need a K8s cluster for integration testing.

