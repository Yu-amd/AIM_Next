#!/bin/bash
#
# Quick Start Script for vLLM Integration
# 
# This script demonstrates the complete workflow:
# 1. Build vLLM container
# 2. Deploy model to Kubernetes
# 3. Test with CLI and web applications
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
MODEL_ID="${1:-meta-llama/Llama-3.1-8B-Instruct}"
BUILD_CONTAINER="${BUILD_CONTAINER:-true}"
DEPLOY_MODEL="${DEPLOY_MODEL:-true}"

main() {
    echo "=========================================="
    echo "AIM GPU Sharing - vLLM Quick Start"
    echo "=========================================="
    echo ""
    echo "Model: ${MODEL_ID}"
    echo ""
    
    cd "${PROJECT_ROOT}"
    
    # Step 1: Build container
    if [ "${BUILD_CONTAINER}" = "true" ]; then
        log_info "Step 1: Building vLLM container..."
        if ./docker/build-vllm-container.sh; then
            log_success "Container built successfully"
        else
            log_error "Container build failed"
            exit 1
        fi
        echo ""
    else
        log_info "Skipping container build (BUILD_CONTAINER=false)"
    fi
    
    # Step 2: Deploy model
    if [ "${DEPLOY_MODEL}" = "true" ]; then
        log_info "Step 2: Deploying model to Kubernetes..."
        if ./k8s/deployment/deploy-model.sh "${MODEL_ID}"; then
            log_success "Model deployed successfully"
        else
            log_error "Model deployment failed"
            exit 1
        fi
        echo ""
    else
        log_info "Skipping model deployment (DEPLOY_MODEL=false)"
    fi
    
    # Step 3: Get endpoint
    log_info "Step 3: Getting endpoint information..."
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    NODE_PORT=$(kubectl get svc vllm-model-service -n aim-gpu-sharing -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "8000")
    ENDPOINT="http://${NODE_IP}:${NODE_PORT}/v1"
    
    log_success "Endpoint ready: ${ENDPOINT}"
    echo ""
    
    # Step 4: Test endpoint
    log_info "Step 4: Testing endpoint..."
    sleep 5  # Wait for service to be ready
    
    if curl -s "${ENDPOINT}/models" > /dev/null 2>&1; then
        log_success "Endpoint is responding"
    else
        log_warning "Endpoint not yet ready (may need more time)"
        log_info "You can test later with:"
        echo "  curl ${ENDPOINT}/models"
    fi
    echo ""
    
    # Summary
    echo "=========================================="
    echo "Quick Start Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Test with CLI:"
    echo "   python3 examples/cli/model_client.py --endpoint ${ENDPOINT}"
    echo ""
    echo "2. Test with Web UI:"
    echo "   python3 examples/web/web_app.py --endpoint ${ENDPOINT} --port 5000"
    echo "   Then open: http://localhost:5000"
    echo ""
    echo "3. Test API directly:"
    echo "   curl ${ENDPOINT}/models"
    echo ""
    echo "For more information, see:"
    echo "  - examples/README.md"
    echo "  - VLLM_INTEGRATION.md"
    echo ""
}

main "$@"

