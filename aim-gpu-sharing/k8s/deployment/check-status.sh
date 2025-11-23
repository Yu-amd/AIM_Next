#!/bin/bash
#
# Quick status check script for deployments
#

NAMESPACE="aim-gpu-sharing"

echo "=========================================="
echo "Kubernetes Deployment Status Check"
echo "=========================================="
echo ""

# Check pods
echo "📦 Pods:"
kubectl get pods -n ${NAMESPACE} -o wide
echo ""

# Check deployments
echo "🚀 Deployments:"
kubectl get deployment -n ${NAMESPACE}
echo ""

# Check services
echo "🌐 Services:"
kubectl get svc -n ${NAMESPACE}
echo ""

# Check pod status details
echo "📋 Pod Status Details:"
for pod in $(kubectl get pods -n ${NAMESPACE} -o jsonpath='{.items[*].metadata.name}'); do
    echo ""
    echo "Pod: $pod"
    kubectl get pod $pod -n ${NAMESPACE} -o jsonpath='  Status: {.status.phase}{"\n"}' 2>/dev/null
    kubectl get pod $pod -n ${NAMESPACE} -o jsonpath='  Ready: {.status.containerStatuses[0].ready}{"\n"}' 2>/dev/null
    kubectl get pod $pod -n ${NAMESPACE} -o jsonpath='  Restarts: {.status.containerStatuses[0].restartCount}{"\n"}' 2>/dev/null
done
echo ""

# Check recent events
echo "📰 Recent Events:"
kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -5
echo ""

# Check if pods are stuck
echo "⚠️  Pod Issues (if any):"
kubectl get pods -n ${NAMESPACE} -o json | \
  jq -r '.items[] | select(.status.phase != "Running" and .status.phase != "Succeeded") | "\(.metadata.name): \(.status.phase) - \(.status.containerStatuses[0].state.waiting.reason // .status.containerStatuses[0].state.terminated.reason // "Unknown")"' 2>/dev/null || \
  kubectl get pods -n ${NAMESPACE} | grep -v Running | grep -v Completed || echo "  All pods running"
echo ""

echo "=========================================="
echo "Quick Commands:"
echo "  View logs: kubectl logs -n ${NAMESPACE} -l app=web-app"
echo "  Describe: kubectl describe pod -n ${NAMESPACE} <pod-name>"
echo "  Watch: kubectl get pods -n ${NAMESPACE} -w"
echo "=========================================="

