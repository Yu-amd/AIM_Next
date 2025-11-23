#!/bin/bash
#
# Deploy vLLM Model to Kubernetes with GPU Sharing
# Based on AIM-Engine workflow: https://github.com/Yu-amd/aim-engine
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
MODEL_ID="${1:-Qwen/Qwen2.5-7B-Instruct}"
PARTITION_ID="${2:-}"
NAMESPACE="aim-gpu-sharing"
DEPLOYMENT_FILE="k8s/deployment/model-deployment.yaml"

usage() {
    echo "Usage: $0 [model-id] [partition-id]"
    echo ""
    echo "Examples:"
    echo "  $0 Qwen/Qwen2.5-7B-Instruct"
    echo "  $0 Qwen/Qwen2.5-7B-Instruct 0"
    echo ""
    exit 1
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

deploy_model() {
    log_info "Deploying model: ${MODEL_ID}"
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Update deployment with model ID
    if [ -n "${PARTITION_ID}" ]; then
        log_info "Using GPU partition: ${PARTITION_ID}"
        kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-model-deployment
  namespace: ${NAMESPACE}
  labels:
    app: vllm-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-model
  template:
    metadata:
      labels:
        app: vllm-model
    spec:
      containers:
      - name: vllm-server
        image: aim-gpu-sharing-vllm:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MODEL_ID
          value: "${MODEL_ID}"
        - name: VLLM_USE_ROCM
          value: "1"
        - name: PYTORCH_ROCM_ARCH
          value: "gfx90a"
        - name: AIM_PARTITION_ID
          value: "${PARTITION_ID}"
        command: ["/bin/bash", "-c"]
        args:
          - |
            echo "Starting vLLM server for model: \$MODEL_ID"
            python3 -m vllm.entrypoints.openai.api_server \\
              --model \$MODEL_ID \\
              --host 0.0.0.0 \\
              --port 8000 \\
              --gpu-memory-utilization 0.95
        resources:
          requests:
            amd.com/gpu: "1"
            memory: "16Gi"
            cpu: "4"
          limits:
            amd.com/gpu: "1"
            memory: "32Gi"
            cpu: "8"
        volumeMounts:
        - name: model-cache
          mountPath: /workspace/model-cache
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
      nodeSelector:
        amd.com/gpu: "true"
EOF
    else
        # Use default deployment file
        sed "s|value: \".*\"|value: \"${MODEL_ID}\"|g" ${DEPLOYMENT_FILE} | kubectl apply -f -
    fi
    
    # Create PVC if it doesn't exist
    kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-pvc
  namespace: ${NAMESPACE}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 200Gi
  storageClassName: local-storage
EOF
    
    log_success "Deployment created"
    
    # Wait for deployment
    log_info "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available \
        deployment/vllm-model-deployment \
        -n ${NAMESPACE} \
        --timeout=300s || {
        log_error "Deployment failed to become ready"
        kubectl logs -n ${NAMESPACE} -l app=vllm-model --tail=50
        exit 1
    }
    
    log_success "Model deployed successfully!"
    
    # Get service info
    NODE_PORT=$(kubectl get svc vllm-model-service -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}')
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    
    echo ""
    echo "=========================================="
    echo "Model Deployment Complete"
    echo "=========================================="
    echo "Model: ${MODEL_ID}"
    echo "Endpoint: http://${NODE_IP}:${NODE_PORT}/v1"
    echo ""
    echo "Test the endpoint:"
    echo "  curl http://${NODE_IP}:${NODE_PORT}/v1/models"
    echo ""
}

main() {
    if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        usage
    fi
    
    check_prerequisites
    deploy_model
}

main "$@"

