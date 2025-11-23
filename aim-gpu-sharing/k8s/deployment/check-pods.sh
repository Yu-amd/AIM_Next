#!/bin/bash
#
# Quick script to check Kubernetes pod workloads
#

NAMESPACE="${1:-aim-gpu-sharing}"

echo "=========================================="
echo "Kubernetes Pod Workloads - $NAMESPACE"
echo "=========================================="
echo ""

# All pods
echo "📦 Pods:"
kubectl get pods -n ${NAMESPACE} -o wide
echo ""

# Deployments
echo "🚀 Deployments:"
kubectl get deployment -n ${NAMESPACE}
echo ""

# Services
echo "🌐 Services:"
kubectl get svc -n ${NAMESPACE}
echo ""

# Resource usage (if available)
echo "📊 Resource Usage:"
kubectl top pods -n ${NAMESPACE} 2>/dev/null || echo "  (Metrics server not available)"
echo ""

# Pod status summary
echo "📋 Status Summary:"
kubectl get pods -n ${NAMESPACE} -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.status.containerStatuses[0].ready}{"\n"}{end}' | column -t
echo ""

# Resource requests/limits
echo "💾 Resource Requests/Limits:"
kubectl get pods -n ${NAMESPACE} -o json | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for pod in data['items']:
    name = pod['metadata']['name']
    containers = pod['spec'].get('containers', [])
    for c in containers:
        res = c.get('resources', {})
        req = res.get('requests', {})
        lim = res.get('limits', {})
        print(f\"{name}: {c['name']}\")
        if req:
            print(f\"  Requests: {req}\")
        if lim:
            print(f\"  Limits: {lim}\")
" 2>/dev/null || echo "  (Unable to parse resources)"
echo ""

echo "=========================================="
echo "Quick Commands:"
echo "  View logs: kubectl logs -n ${NAMESPACE} <pod-name>"
echo "  Describe: kubectl describe pod -n ${NAMESPACE} <pod-name>"
echo "  Watch: kubectl get pods -n ${NAMESPACE} -w"
echo "=========================================="

