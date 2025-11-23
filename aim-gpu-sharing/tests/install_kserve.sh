#!/bin/bash
#
# KServe Installation Script
# 
# This script installs KServe in a Kubernetes cluster for testing purposes.
# It handles prerequisites, installation, and verification.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KSERVE_VERSION="${KSERVE_VERSION:-v0.12.0}"
KSERVE_NAMESPACE="${KSERVE_NAMESPACE:-kserve}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.13.0}"
ISTIO_VERSION="${ISTIO_VERSION:-1.20.0}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Logging functions
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

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "kubectl is available and cluster is accessible"
}

# Check if cluster meets requirements
check_cluster_requirements() {
    log_info "Checking cluster requirements..."
    
    # Check Kubernetes version (KServe requires 1.20+)
    k8s_version=$(kubectl version -o json 2>/dev/null | grep -oP '"gitVersion": "\K[^"]*' | head -1 || echo "")
    if [ -z "$k8s_version" ]; then
        log_warning "Could not determine Kubernetes version, continuing anyway"
    else
        log_info "Kubernetes version: $k8s_version"
    fi
    
    # Check if cert-manager is installed
    if kubectl get crd certificates.cert-manager.io &> /dev/null; then
        log_success "cert-manager is already installed"
        CERT_MANAGER_INSTALLED=true
    else
        log_info "cert-manager not found, will install it"
        CERT_MANAGER_INSTALLED=false
    fi
    
    # Check if Istio is installed (optional but recommended)
    if kubectl get crd virtualservices.networking.istio.io &> /dev/null; then
        log_success "Istio is already installed"
        ISTIO_INSTALLED=true
    else
        log_warning "Istio not found (optional, but recommended for production)"
        ISTIO_INSTALLED=false
    fi
}

# Install cert-manager
install_cert_manager() {
    if [ "$CERT_MANAGER_INSTALLED" = true ]; then
        log_info "cert-manager already installed, skipping"
        return 0
    fi
    
    log_info "Installing cert-manager ${CERT_MANAGER_VERSION}..."
    
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml
    
    log_info "Waiting for cert-manager to be ready..."
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/instance=cert-manager \
        -n cert-manager \
        --timeout=300s || {
        log_error "cert-manager failed to become ready"
        return 1
    }
    
    log_success "cert-manager installed successfully"
}

# Install Istio (optional)
install_istio() {
    if [ "$ISTIO_INSTALLED" = true ]; then
        log_info "Istio already installed, skipping"
        return 0
    fi
    
    log_info "Installing Istio ${ISTIO_VERSION}..."
    
    # Download istioctl if not available
    if ! command -v istioctl &> /dev/null; then
        log_info "Downloading istioctl..."
        ISTIO_DOWNLOAD_URL="https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/istio-${ISTIO_VERSION}-linux-amd64.tar.gz"
        curl -L "${ISTIO_DOWNLOAD_URL}" | tar -xz
        export PATH="${PWD}/istio-${ISTIO_VERSION}/bin:${PATH}"
    fi
    
    # Install Istio with minimal profile
    istioctl install --set profile=minimal -y || {
        log_warning "Istio installation failed, but KServe can work without it"
        return 0
    }
    
    log_success "Istio installed successfully"
}

# Install KServe
install_kserve() {
    log_info "Installing KServe ${KSERVE_VERSION}..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "${KSERVE_NAMESPACE}" &> /dev/null; then
        kubectl create namespace "${KSERVE_NAMESPACE}"
        log_info "Created namespace: ${KSERVE_NAMESPACE}"
    fi
    
    # Install KServe using kubectl apply
    log_info "Applying KServe manifests..."
    kubectl apply -f https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve.yaml
    
    # Also install KServe RBAC (if available - some versions don't have separate RBAC file)
    if curl -s -o /dev/null -w "%{http_code}" https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-rbac.yaml | grep -q "200"; then
        kubectl apply -f https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-rbac.yaml
    else
        log_info "KServe RBAC file not found (may be included in main manifest)"
    fi
    
    log_info "Waiting for KServe to be ready..."
    
    # Wait for KServe controller
    kubectl wait --for=condition=ready pod \
        -l control-plane=kserve-controller-manager \
        -n "${KSERVE_NAMESPACE}" \
        --timeout=300s || {
        log_error "KServe controller failed to become ready"
        return 1
    }
    
    log_success "KServe installed successfully"
}

# Verify KServe installation
verify_kserve() {
    log_info "Verifying KServe installation..."
    
    # Check if InferenceService CRD exists
    if kubectl get crd inferenceservices.serving.kserve.io &> /dev/null; then
        log_success "InferenceService CRD is installed"
    else
        log_error "InferenceService CRD not found"
        return 1
    fi
    
    # Check if KServe controller is running
    if kubectl get pods -n "${KSERVE_NAMESPACE}" -l control-plane=kserve-controller-manager | grep -q Running; then
        log_success "KServe controller is running"
    else
        log_error "KServe controller is not running"
        return 1
    fi
    
    # Check KServe version
    kserve_version=$(kubectl get deployment kserve-controller-manager -n "${KSERVE_NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "")
    if [ -n "$kserve_version" ]; then
        log_info "KServe controller image: $kserve_version"
    fi
    
    log_success "KServe verification completed"
}

# Print installation summary
print_summary() {
    echo ""
    echo "=========================================="
    echo "KServe Installation Summary"
    echo "=========================================="
    echo "KServe Version: ${KSERVE_VERSION}"
    echo "Namespace: ${KSERVE_NAMESPACE}"
    echo "cert-manager: ${CERT_MANAGER_INSTALLED}"
    echo "Istio: ${ISTIO_INSTALLED}"
    echo ""
    echo "To verify installation, run:"
    echo "  kubectl get pods -n ${KSERVE_NAMESPACE}"
    echo "  kubectl get crd | grep kserve"
    echo ""
    echo "To test KServe, create an InferenceService:"
    echo "  kubectl apply -f - <<EOF"
    echo "  apiVersion: serving.kserve.io/v1beta1"
    echo "  kind: InferenceService"
    echo "  metadata:"
    echo "    name: sklearn-iris"
    echo "  spec:"
    echo "    predictor:"
    echo "      sklearn:"
    echo "        storageUri: gs://kfserving-examples/models/sklearn/iris"
    echo "  EOF"
    echo "=========================================="
}

# Main installation function
main() {
    echo "=========================================="
    echo "KServe Installation Script"
    echo "=========================================="
    echo ""
    
    check_kubectl
    check_cluster_requirements
    
    # Install prerequisites
    install_cert_manager
    
    # Install KServe
    install_kserve
    
    # Verify installation
    verify_kserve
    
    print_summary
    
    log_success "KServe installation completed successfully!"
}

# Handle script arguments
case "${1:-install}" in
    install)
        main
        ;;
    verify)
        check_kubectl
        verify_kserve
        ;;
    uninstall)
        log_warning "Uninstalling KServe..."
        kubectl delete -f https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve.yaml || true
        # Try to delete RBAC file if it exists
        if curl -s -o /dev/null -w "%{http_code}" https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-rbac.yaml | grep -q "200"; then
            kubectl delete -f https://github.com/kserve/kserve/releases/download/${KSERVE_VERSION}/kserve-rbac.yaml || true
        fi
        kubectl delete namespace "${KSERVE_NAMESPACE}" || true
        log_success "KServe uninstalled"
        ;;
    *)
        echo "Usage: $0 [install|verify|uninstall]"
        echo ""
        echo "Commands:"
        echo "  install   - Install KServe (default)"
        echo "  verify    - Verify KServe installation"
        echo "  uninstall - Uninstall KServe"
        exit 1
        ;;
esac

