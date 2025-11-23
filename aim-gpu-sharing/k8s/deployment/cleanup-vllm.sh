#!/bin/bash
#
# Cleanup all vLLM instances (Docker and Kubernetes)
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

echo "=========================================="
echo "Cleaning up all vLLM instances"
echo "=========================================="
echo ""

# Cleanup Docker containers
log_info "Cleaning up Docker containers..."
VLLM_CONTAINERS=$(docker ps -a --filter "name=vllm" --format "{{.Names}}" 2>/dev/null || true)

if [ -n "$VLLM_CONTAINERS" ]; then
    echo "$VLLM_CONTAINERS" | while read container; do
        log_info "  Stopping container: $container"
        docker stop "$container" 2>/dev/null || true
    done
    
    echo "$VLLM_CONTAINERS" | while read container; do
        log_info "  Removing container: $container"
        docker rm "$container" 2>/dev/null || true
    done
    log_success "Docker containers cleaned up"
else
    log_info "No vLLM Docker containers found"
fi

echo ""

# Cleanup Kubernetes resources
log_info "Cleaning up Kubernetes resources..."

NAMESPACE="aim-gpu-sharing"

# Delete deployment
if kubectl get deployment vllm-model-deployment -n ${NAMESPACE} &>/dev/null; then
    log_info "  Deleting vLLM deployment..."
    kubectl delete deployment vllm-model-deployment -n ${NAMESPACE} --wait=true --timeout=60s 2>/dev/null || true
    log_success "Deployment deleted"
else
    log_info "No vLLM deployment found"
fi

# Delete service
if kubectl get svc vllm-model-service -n ${NAMESPACE} &>/dev/null; then
    log_info "  Deleting vLLM service..."
    kubectl delete svc vllm-model-service -n ${NAMESPACE} 2>/dev/null || true
    log_success "Service deleted"
else
    log_info "No vLLM service found"
fi

# Delete PVC (optional, comment out if you want to keep data)
if kubectl get pvc model-cache-pvc -n ${NAMESPACE} &>/dev/null; then
    log_info "  Deleting PVC..."
    kubectl delete pvc model-cache-pvc -n ${NAMESPACE} 2>/dev/null || true
    log_success "PVC deleted"
else
    log_info "No PVC found"
fi

echo ""

# Verify cleanup
log_info "Verifying cleanup..."

DOCKER_REMAINING=$(docker ps -a --filter "name=vllm" --format "{{.Names}}" 2>/dev/null | wc -l)
K8S_PODS=$(kubectl get pods -n ${NAMESPACE} -l app=vllm-model 2>/dev/null | grep -v NAME | wc -l)

if [ "$DOCKER_REMAINING" -eq 0 ] && [ "$K8S_PODS" -eq 0 ]; then
    log_success "All vLLM instances cleaned up!"
else
    log_warning "Some instances may still exist:"
    [ "$DOCKER_REMAINING" -gt 0 ] && log_warning "  Docker containers: $DOCKER_REMAINING"
    [ "$K8S_PODS" -gt 0 ] && log_warning "  Kubernetes pods: $K8S_PODS"
fi

echo ""
echo "=========================================="
echo "Cleanup complete"
echo "=========================================="
echo ""
echo "Ready to deploy fresh vLLM instance:"
echo "  ./k8s/deployment/deploy-model.sh Qwen/Qwen2.5-7B-Instruct"
echo ""

