#!/bin/bash
#
# Deploy Second vLLM Model for GPU Sharing Validation
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
MODEL_ID="${1:-Qwen/Qwen2.5-7B-Instruct}"
MEMORY_UTIL="${2:-0.4}"  # Use 40% GPU memory to fit both models
NAMESPACE="aim-gpu-sharing"

echo "=========================================="
echo "Deploying Second vLLM Model"
echo "=========================================="
echo ""
echo "Model: $MODEL_ID"
echo "GPU Memory Utilization: $MEMORY_UTIL (40% to fit both models)"
echo ""

# Check if first instance exists
log_info "Checking existing vLLM instances..."
FIRST_POD=$(kubectl get pods -n ${NAMESPACE} -l app=vllm-model -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -z "$FIRST_POD" ]; then
    log_warning "No first vLLM instance found. Deploying first instance..."
    ./k8s/deployment/deploy-model.sh "$MODEL_ID"
    sleep 10
fi

# Check if second instance already exists
EXISTING=$(kubectl get deployment -n ${NAMESPACE} vllm-model-deployment-2 2>/dev/null || echo "")
if [ -n "$EXISTING" ]; then
    log_warning "Second deployment already exists. Deleting..."
    kubectl delete deployment vllm-model-deployment-2 -n ${NAMESPACE}
    kubectl delete svc vllm-model-service-2 -n ${NAMESPACE} 2>/dev/null || true
    sleep 5
fi

# Create namespace if needed
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Update deployment with model and memory settings
log_info "Creating second vLLM deployment..."
log_warning "Note: Second instance will share GPU with first instance (no exclusive GPU request)"
cat k8s/deployment/vllm-model-deployment-2.yaml | \
  sed "s|value: \"Qwen/Qwen2.5-7B-Instruct\"|value: \"${MODEL_ID}\"|g" | \
  sed "s|--gpu-memory-utilization 0.4|--gpu-memory-utilization ${MEMORY_UTIL}|g" | \
  kubectl apply -f -

log_success "Deployment created"

# Wait for deployment
log_info "Waiting for pod to be ready..."
kubectl wait --for=condition=available \
  deployment/vllm-model-deployment-2 \
  -n ${NAMESPACE} \
  --timeout=300s || {
    log_error "Deployment failed to become ready"
    kubectl logs -n ${NAMESPACE} -l app=vllm-model-2 --tail=50
    exit 1
}

log_success "Second vLLM model deployed successfully!"

# Get service info
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
NODE_PORT=$(kubectl get svc vllm-model-service-2 -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30081")

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo ""
echo "First Instance:"
echo "  Service: vllm-model-service (NodePort 30080)"
echo "  URL: http://${NODE_IP}:30080/v1"
echo ""
echo "Second Instance:"
echo "  Service: vllm-model-service-2 (NodePort ${NODE_PORT})"
echo "  URL: http://${NODE_IP}:${NODE_PORT}/v1"
echo ""
echo "Test both endpoints:"
echo "  curl http://${NODE_IP}:30080/v1/models"
echo "  curl http://${NODE_IP}:${NODE_PORT}/v1/models"
echo ""
echo "Validate GPU sharing:"
echo "  ./validate-gpu-sharing.sh"
echo "  amd-smi | grep -A 10 Processes"
echo ""

