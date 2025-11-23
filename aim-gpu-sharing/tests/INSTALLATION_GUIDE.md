# KServe Installation Guide

This guide explains how to install KServe for testing the AIM GPU Sharing integration.

## Quick Start

```bash
cd aim-gpu-sharing/tests
./install_kserve.sh install
```

## Prerequisites

### 1. Kubernetes Cluster with AMD GPU Operator

Before installing KServe, you need a Kubernetes cluster with AMD GPU operator installed.

**Recommended Setup:** Use the [Kubernetes-MI300X repository](https://github.com/Yu-amd/Kubernetes-MI300X) for automated setup:

```bash
# Clone the setup repository
git clone https://github.com/Yu-amd/Kubernetes-MI300X.git
cd Kubernetes-MI300X

# Step 1: Install Kubernetes
sudo ./install-kubernetes.sh

# Step 2: Install AMD GPU Operator
./install-amd-gpu-operator.sh

# Verify GPU operator installation
kubectl get pods -n kube-amd-gpu
```

**Alternative:** If you already have a Kubernetes cluster, install the AMD GPU operator manually following the [official documentation](https://github.com/RadeonOpenCompute/k8s-device-plugin).

### 2. Cluster Requirements

- Kubernetes cluster (v1.20 or higher)
- kubectl configured to access the cluster
- Sufficient cluster resources (at least 2 CPU cores and 4GB RAM available)
- Network access to download KServe manifests

## Installation Steps

### 1. Automatic Installation

The installation script handles everything automatically:

```bash
./install_kserve.sh install
```

This will:
1. Check cluster connectivity
2. Install cert-manager (if not present)
3. Install KServe
4. Verify the installation

### 2. Manual Verification

After installation, verify KServe is working:

```bash
# Check KServe controller
kubectl get pods -n kserve

# Check InferenceService CRD
kubectl get crd inferenceservices.serving.kserve.io

# Verify installation
./install_kserve.sh verify
```

### 3. Test Installation

Create a simple InferenceService to test:

```bash
kubectl apply -f - <<EOF
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    sklearn:
      storageUri: gs://kfserving-examples/models/sklearn/iris
EOF
```

Check the status:

```bash
kubectl get inferenceservice sklearn-iris
```

## Configuration Options

You can customize the installation with environment variables:

```bash
export KSERVE_VERSION=v0.12.0        # KServe version
export KSERVE_NAMESPACE=kserve       # Namespace for KServe
export CERT_MANAGER_VERSION=v1.13.0   # cert-manager version
./install_kserve.sh install
```

## Troubleshooting

### Installation Fails

**Problem:** cert-manager installation fails

**Solution:**
```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

**Problem:** KServe controller doesn't start

**Solution:**
```bash
# Check controller logs
kubectl logs -n kserve -l control-plane=kserve-controller-manager

# Check events
kubectl get events -n kserve --sort-by='.lastTimestamp'
```

### Cluster Resource Issues

If you're running on a resource-constrained cluster:

1. **Minimal cert-manager:**
   ```bash
   kubectl scale deployment cert-manager -n cert-manager --replicas=1
   ```

2. **Check resource usage:**
   ```bash
   kubectl top nodes
   kubectl top pods -n kserve
   ```

### Network Issues

If you can't download manifests:

1. **Use local manifests:**
   - Download KServe manifests manually
   - Modify the script to use local files

2. **Check proxy settings:**
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```

## Uninstallation

To remove KServe:

```bash
./install_kserve.sh uninstall
```

This will:
- Delete KServe resources
- Delete KServe namespace
- **Note:** cert-manager is NOT uninstalled (it may be used by other components)

## Integration with Tests

The test infrastructure automatically detects if KServe is installed:

```bash
# Run all tests (will skip E2E if KServe not installed)
python3 tests/run_all_tests.py

# Install KServe and run all tests
cd tests
./install_kserve.sh install
cd ..
python3 tests/run_all_tests.py
```

Or use the convenience script:

```bash
./tests/run_tests_with_kserve.sh --install-kserve
```

## Version Compatibility

| KServe Version | Kubernetes | cert-manager | Notes |
|----------------|------------|--------------|-------|
| v0.12.0        | 1.20+      | v1.13.0      | Recommended |
| v0.11.0        | 1.20+      | v1.12.0      | Supported |
| v0.10.0        | 1.19+      | v1.11.0      | Legacy |

## Next Steps

After installing KServe:

1. **Run E2E tests:**
   ```bash
   python3 tests/test_kserve_e2e.py
   ```

2. **Deploy GPU Sharing Operator:**
   ```bash
   cd k8s/operator
   ./install.sh
   ```

3. **Create InferenceService with GPU sharing:**
   See examples in the main README

## Additional Resources

- [KServe Documentation](https://kserve.github.io/website/)
- [KServe GitHub](https://github.com/kserve/kserve)
- [cert-manager Documentation](https://cert-manager.io/docs/)

