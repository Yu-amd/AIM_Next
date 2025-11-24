#!/bin/bash
# Cleanup script for fine-tuning resources

set -e

NAMESPACE="${NAMESPACE:-aim-finetuning}"

echo "=== Cleaning Up Fine-Tuning Resources ==="
echo ""

echo "1. Deleting all FineTuningJobs..."
kubectl delete finetuningjob --all -n "$NAMESPACE" 2>/dev/null || echo "  No FineTuningJobs found"

echo ""
echo "2. Deleting all training pods..."
kubectl delete pod -n "$NAMESPACE" -l app=finetuning 2>/dev/null || echo "  No training pods with label found"
kubectl delete pod -n "$NAMESPACE" qwen-lora-finetune-pod 2>/dev/null || echo "  No qwen-lora-finetune-pod found"

echo ""
echo "3. Stopping local controller processes..."
pkill -f finetuning_controller.py 2>/dev/null && echo "  ✓ Controller stopped" || echo "  No controller process found"

echo ""
echo "4. Checking for remaining resources..."
echo "Pods:"
kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "  No pods found"
echo ""
echo "FineTuningJobs:"
kubectl get finetuningjob -n "$NAMESPACE" 2>/dev/null || echo "  No FineTuningJobs found"

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "To start fresh:"
echo "  1. kubectl apply -f k8s/examples/finetuning-job-example.yaml"
echo "  2. Run controller: cd k8s/controller && python3 finetuning_controller.py"

