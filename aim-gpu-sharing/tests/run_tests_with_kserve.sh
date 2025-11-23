#!/bin/bash
#
# Test Runner with Optional KServe Installation
#
# This script optionally installs KServe and then runs all tests.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if KServe is installed
check_kserve() {
    if kubectl get crd inferenceservices.serving.kserve.io &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Main execution
main() {
    cd "${PROJECT_ROOT}"
    
    log_info "AIM GPU Sharing - Test Runner"
    echo ""
    
    # Check if KServe is installed
    if check_kserve; then
        log_success "KServe is already installed"
        INSTALL_KSERVE=false
    else
        log_warning "KServe is not installed"
        read -p "Do you want to install KServe now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            INSTALL_KSERVE=true
        else
            INSTALL_KSERVE=false
            log_info "Skipping KServe installation. E2E tests will be skipped."
        fi
    fi
    
    # Install KServe if requested
    if [ "$INSTALL_KSERVE" = true ]; then
        log_info "Installing KServe..."
        cd "${SCRIPT_DIR}"
        ./install_kserve.sh install
        cd "${PROJECT_ROOT}"
        
        if ! check_kserve; then
            log_warning "KServe installation may have failed, but continuing with tests"
        else
            log_success "KServe installed successfully"
        fi
    fi
    
    # Run tests
    log_info "Running test suite..."
    echo ""
    
    python3 tests/run_all_tests.py
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_warning "Some tests failed (exit code: $exit_code)"
    fi
    
    return $exit_code
}

# Handle command line arguments
case "${1:-}" in
    --install-kserve)
        INSTALL_KSERVE=true
        shift
        ;;
    --skip-kserve)
        INSTALL_KSERVE=false
        shift
        ;;
    --help)
        echo "Usage: $0 [--install-kserve|--skip-kserve]"
        echo ""
        echo "Options:"
        echo "  --install-kserve  Install KServe before running tests"
        echo "  --skip-kserve     Skip KServe installation (default if not installed)"
        echo "  --help            Show this help message"
        exit 0
        ;;
esac

main "$@"

