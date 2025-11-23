#!/bin/bash
# Installation script for AIM GPU Sharing Operator

set -e

NAMESPACE="aim-system"

echo "Installing AIM GPU Sharing Operator..."

# Create namespace
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC
echo "Applying RBAC..."
kubectl apply -f k8s/operator/rbac.yaml

# Apply CRD
echo "Applying CRD..."
kubectl apply -f k8s/crd/gpu-sharing-crd.yaml

# Wait for CRD to be ready
echo "Waiting for CRD to be ready..."
kubectl wait --for=condition=Established crd/inferenceservices.aim.amd.com --timeout=60s

# Apply operator deployment
echo "Applying operator deployment..."
kubectl apply -f k8s/operator/gpu-sharing-operator.yaml

# Wait for operator to be ready
echo "Waiting for operator to be ready..."
kubectl wait --for=condition=available deployment/aim-gpu-sharing-operator -n ${NAMESPACE} --timeout=120s

echo "✅ AIM GPU Sharing Operator installed successfully!"
echo ""
echo "Check operator status:"
echo "  kubectl get pods -n ${NAMESPACE}"
echo "  kubectl logs -n ${NAMESPACE} -l app=aim-gpu-sharing-operator"

