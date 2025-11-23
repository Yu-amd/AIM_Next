#!/bin/bash
#
# GPU Sharing/Partitioning Validation Script
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
echo "GPU Sharing/Partitioning Validation"
echo "=========================================="
echo ""

# 1. Check amd-smi availability
log_info "1. Checking amd-smi availability..."
if command -v amd-smi &> /dev/null; then
    log_success "amd-smi is available"
else
    log_error "amd-smi not found. GPU sharing validation requires amd-smi."
    exit 1
fi
echo ""

# 2. Check partition mode
log_info "2. GPU Partition Mode:"
COMPUTE_PARTITION=$(amd-smi --show-compute-partition 2>/dev/null | grep -i "compute partition" | awk '{print $3}' || echo "Unknown")
if [ "$COMPUTE_PARTITION" = "CPX" ]; then
    log_success "CPX mode detected (8 partitions for MI300X)"
    EXPECTED_PARTITIONS=8
elif [ "$COMPUTE_PARTITION" = "SPX" ]; then
    log_success "SPX mode detected (1 partition)"
    EXPECTED_PARTITIONS=1
else
    log_warning "Partition mode: $COMPUTE_PARTITION"
    EXPECTED_PARTITIONS=1
fi
echo ""

# 3. Check logical devices
log_info "3. Logical Devices (Partitions):"
DEVICE_COUNT=$(amd-smi -L 2>/dev/null | wc -l)
if [ "$DEVICE_COUNT" -eq "$EXPECTED_PARTITIONS" ]; then
    log_success "Found $DEVICE_COUNT device(s) (expected $EXPECTED_PARTITIONS)"
else
    log_warning "Found $DEVICE_COUNT device(s), expected $EXPECTED_PARTITIONS"
fi
amd-smi -L 2>/dev/null | head -10
echo ""

# 4. Check memory partition
log_info "4. Memory Partition Mode:"
MEMORY_PARTITION=$(amd-smi --show-memory-partition 2>/dev/null | grep -i "memory partition" | awk '{print $3}' || echo "Unknown")
echo "Memory Partition: $MEMORY_PARTITION"
echo ""

# 5. Check GPU memory usage
log_info "5. GPU Memory Usage:"
amd-smi --showmeminfo vram 2>/dev/null | head -15 || log_warning "Could not get memory info"
echo ""

# 6. Check running vLLM instances
log_info "6. Running vLLM Instances:"

# Docker
if command -v docker &> /dev/null; then
    DOCKER_CONTAINERS=$(docker ps --format "{{.Names}}" | grep -E "vllm|vLLM" || true)
    if [ -n "$DOCKER_CONTAINERS" ]; then
        echo "Docker containers:"
        echo "$DOCKER_CONTAINERS" | while read name; do
            echo "  - $name"
            PARTITION_ID=$(docker exec $name env 2>/dev/null | grep -i "PARTITION_ID" | cut -d= -f2 || echo "not set")
            echo "    Partition ID: ${PARTITION_ID:-not set}"
        done
    else
        echo "  No Docker vLLM containers found"
    fi
fi

# Kubernetes
if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then
    K8S_PODS=$(kubectl get pods -n aim-gpu-sharing -l app=vllm-model -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$K8S_PODS" ]; then
        echo "Kubernetes pods:"
        for pod in $K8S_PODS; do
            echo "  - $pod"
            PARTITION_ID=$(kubectl exec -n aim-gpu-sharing $pod -- env 2>/dev/null | grep -i "PARTITION_ID" | cut -d= -f2 || echo "not set")
            echo "    Partition ID: ${PARTITION_ID:-not set}"
        done
    else
        echo "  No Kubernetes vLLM pods found"
    fi
fi
echo ""

# 7. Check GPU utilization
log_info "7. GPU Utilization:"
amd-smi --showuse 2>/dev/null | head -10 || log_warning "Could not get utilization info"
echo ""

# 8. Validate GPU sharing
log_info "8. GPU Sharing Validation:"
INSTANCE_COUNT=0
if command -v docker &> /dev/null; then
    DOCKER_COUNT=$(docker ps --format "{{.Names}}" | grep -E "vllm|vLLM" | wc -l)
    INSTANCE_COUNT=$((INSTANCE_COUNT + DOCKER_COUNT))
fi
if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then
    K8S_COUNT=$(kubectl get pods -n aim-gpu-sharing -l app=vllm-model --no-headers 2>/dev/null | wc -l)
    INSTANCE_COUNT=$((INSTANCE_COUNT + K8S_COUNT))
fi

if [ "$INSTANCE_COUNT" -gt 1 ]; then
    log_success "Multiple vLLM instances detected ($INSTANCE_COUNT) - GPU sharing is active"
    if [ "$EXPECTED_PARTITIONS" -gt 1 ]; then
        log_success "CPX mode with $EXPECTED_PARTITIONS partitions - each model can use different partition"
    else
        log_warning "SPX mode (1 partition) - models share same partition"
    fi
elif [ "$INSTANCE_COUNT" -eq 1 ]; then
    log_info "Single vLLM instance detected - deploy second instance to test GPU sharing"
else
    log_warning "No vLLM instances detected - deploy models first"
fi
echo ""

# 9. Check partition assignment
log_info "9. Partition Assignment Check:"
if [ "$INSTANCE_COUNT" -gt 1 ] && [ "$EXPECTED_PARTITIONS" -gt 1 ]; then
    log_info "Multiple instances in CPX mode - verify each uses different partition"
    log_info "Check partition IDs in environment variables above"
else
    log_info "Single partition mode or single instance - partition assignment not critical"
fi
echo ""

echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo ""
echo "Partition Mode: $COMPUTE_PARTITION"
echo "Expected Partitions: $EXPECTED_PARTITIONS"
echo "Detected Devices: $DEVICE_COUNT"
echo "vLLM Instances: $INSTANCE_COUNT"
echo ""
if [ "$INSTANCE_COUNT" -gt 1 ] && [ "$EXPECTED_PARTITIONS" -gt 1 ]; then
    log_success "GPU sharing validation: PASSED"
    echo "  - Multiple instances running"
    echo "  - CPX mode with multiple partitions"
    echo "  - Ready for multi-model deployment"
elif [ "$INSTANCE_COUNT" -gt 1 ]; then
    log_warning "GPU sharing validation: PARTIAL"
    echo "  - Multiple instances running"
    echo "  - SPX mode (single partition) - models share resources"
elif [ "$INSTANCE_COUNT" -eq 1 ]; then
    log_info "GPU sharing validation: SINGLE INSTANCE"
    echo "  - Deploy second instance to test GPU sharing"
else
    log_warning "GPU sharing validation: NO INSTANCES"
    echo "  - Deploy vLLM models first"
fi
echo ""

