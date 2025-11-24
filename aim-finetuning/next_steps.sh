#!/bin/bash
# Next steps after Docker build completes

echo "=== After Docker Build Completes ==="
echo ""

echo "1. Import image into containerd (K8s uses containerd, not Docker):"
echo "   docker save aim-finetuning:latest | sudo ctr -n k8s.io images import -"
echo ""

echo "2. Delete and recreate the pod (to pick up the image):"
echo "   kubectl delete pod qwen-lora-finetune-pod -n aim-finetuning"
echo "   # The controller will automatically recreate it"
echo ""

echo "3. Monitor the training pod:"
echo "   kubectl get pod qwen-lora-finetune-pod -n aim-finetuning -w"
echo "   kubectl logs -n aim-finetuning qwen-lora-finetune-pod -f"
echo ""

echo "4. Monitor the FineTuningJob status:"
echo "   kubectl get finetuningjob qwen-lora-finetune -n aim-finetuning -w"
echo "   kubectl describe finetuningjob qwen-lora-finetune -n aim-finetuning"
echo ""

echo "5. Check for checkpoints and AIM profile:"
echo "   kubectl exec -n aim-finetuning qwen-lora-finetune-pod -- ls -lh /workspace/output/"
echo ""

echo "The training should start automatically once the pod is running!"
