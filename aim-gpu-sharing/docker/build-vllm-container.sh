#!/bin/bash
#
# Build vLLM Container for AIM GPU Sharing
# Based on AIM-Engine workflow: https://github.com/Yu-amd/aim-engine
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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

# Configuration
IMAGE_NAME="${IMAGE_NAME:-aim-gpu-sharing-vllm}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKERFILE="${DOCKERFILE:-${SCRIPT_DIR}/Dockerfile.aim-vllm}"

main() {
    echo "=========================================="
    echo "Building AIM GPU Sharing + vLLM Container"
    echo "=========================================="
    echo ""
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    log_info "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
    log_info "Dockerfile: ${DOCKERFILE}"
    echo ""
    
    # Change to project root for build context
    cd "${PROJECT_ROOT}"
    
    # Build the image
    docker build -f "${DOCKERFILE}" -t "${IMAGE_NAME}:${IMAGE_TAG}" .
    
    if [ $? -eq 0 ]; then
        log_success "Build completed successfully!"
        echo ""
        echo "Usage examples:"
        echo ""
        echo "  # Generate vLLM command for a model"
        echo "  docker run --rm -it \\"
        echo "    --device=/dev/kfd \\"
        echo "    --device=/dev/dri \\"
        echo "    --group-add=video \\"
        echo "    --group-add=render \\"
        echo "    -v \$(pwd)/model-cache:/workspace/model-cache \\"
        echo "    ${IMAGE_NAME}:${IMAGE_TAG} \\"
        echo "    aim-vllm-generate meta-llama/Llama-3.1-8B-Instruct"
        echo ""
        echo "  # Start vLLM server"
        echo "  docker run --rm -it \\"
        echo "    --device=/dev/kfd \\"
        echo "    --device=/dev/dri \\"
        echo "    --group-add=video \\"
        echo "    --group-add=render \\"
        echo "    -v \$(pwd)/model-cache:/workspace/model-cache \\"
        echo "    -p 8000:8000 \\"
        echo "    ${IMAGE_NAME}:${IMAGE_TAG} \\"
        echo "    aim-vllm-serve meta-llama/Llama-3.1-8B-Instruct"
        echo ""
        echo "  # Interactive shell"
        echo "  docker run --rm -it \\"
        echo "    --device=/dev/kfd \\"
        echo "    --device=/dev/dri \\"
        echo "    --group-add=video \\"
        echo "    --group-add=render \\"
        echo "    -v \$(pwd)/model-cache:/workspace/model-cache \\"
        echo "    -p 8000:8000 \\"
        echo "    ${IMAGE_NAME}:${IMAGE_TAG} \\"
        echo "    aim-shell"
        echo ""
    else
        log_error "Build failed!"
        exit 1
    fi
}

main "$@"

