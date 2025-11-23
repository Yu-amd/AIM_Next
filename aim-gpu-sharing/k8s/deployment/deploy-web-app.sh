#!/bin/bash
#
# Deploy Web Application to Kubernetes
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
VLLM_ENDPOINT="${1:-http://vllm-model-service:8000/v1}"
NAMESPACE="aim-gpu-sharing"
DEPLOYMENT_FILE="k8s/deployment/web-app-deployment.yaml"

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

deploy_web_app() {
    log_info "Deploying web application..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Update deployment with vLLM endpoint
    log_info "Using vLLM endpoint: ${VLLM_ENDPOINT}"
    
    # Apply deployment
    kubectl apply -f ${DEPLOYMENT_FILE}
    
    # Update environment variable if custom endpoint provided
    if [ "${VLLM_ENDPOINT}" != "http://vllm-model-service:8000/v1" ]; then
        log_info "Updating VLLM_ENDPOINT environment variable..."
        kubectl set env deployment/web-app-deployment -n ${NAMESPACE} VLLM_ENDPOINT="${VLLM_ENDPOINT}"
    fi
    
    log_success "Deployment created"
    
    # Wait for deployment
    log_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available \
        deployment/web-app-deployment \
        -n ${NAMESPACE} \
        --timeout=120s || {
        log_error "Deployment failed to become ready"
        kubectl logs -n ${NAMESPACE} -l app=web-app --tail=50
        exit 1
    }
    
    log_success "Web application deployed successfully!"
    
    # Get service info
    NODE_PORT=$(kubectl get svc web-app-service -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30050")
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo "=========================================="
    echo "Web Application Deployment Complete"
    echo "=========================================="
    echo "vLLM Endpoint: ${VLLM_ENDPOINT}"
    echo "Web App URL: http://${NODE_IP}:${NODE_PORT}"
    echo ""
    echo "Access the web UI:"
    echo "  http://${NODE_IP}:${NODE_PORT}"
    echo ""
    echo "Or via port forwarding:"
    echo "  kubectl port-forward -n ${NAMESPACE} svc/web-app-service 5000:5000"
    echo "  Then open: http://localhost:5000"
    echo ""
}

main() {
    check_prerequisites
    deploy_web_app
}

main "$@"

