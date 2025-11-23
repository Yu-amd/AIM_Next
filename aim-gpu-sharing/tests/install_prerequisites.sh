#!/bin/bash
#
# Install Test Prerequisites
#
# This script installs Python dependencies required for running tests.
#

set -euo pipefail

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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Check if pip is available
check_pip() {
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        log_error "pip is not installed. Please install Python and pip first."
        exit 1
    fi
    
    # Use pip3 if available, otherwise pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    else
        PIP_CMD="pip"
    fi
    
    log_success "Found pip: $PIP_CMD"
}

# Install Python packages
install_packages() {
    log_info "Installing test prerequisites..."
    
    # Core testing dependencies
    local packages=(
        "pytest>=7.4.0"
        "pytest-asyncio>=0.21.0"
        "prometheus-client>=0.19.0"
        "pyyaml>=6.0"
    )
    
    # Try to install with --user first (for system-wide Python)
    # If that fails, try without --user
    for package in "${packages[@]}"; do
        log_info "Installing $package..."
        if $PIP_CMD install --user --quiet "$package" 2>/dev/null; then
            log_success "Installed $package"
        elif $PIP_CMD install --break-system-packages --quiet "$package" 2>/dev/null; then
            log_success "Installed $package (with --break-system-packages)"
        elif $PIP_CMD install --quiet "$package" 2>/dev/null; then
            log_success "Installed $package"
        else
            log_warning "Failed to install $package (may already be installed)"
        fi
    done
    
    # Try to install kubernetes client (optional, for E2E tests)
    log_info "Installing kubernetes client (optional)..."
    if $PIP_CMD install --user --quiet "kubernetes>=28.0.0" 2>/dev/null || \
       $PIP_CMD install --break-system-packages --quiet "kubernetes>=28.0.0" 2>/dev/null || \
       $PIP_CMD install --quiet "kubernetes>=28.0.0" 2>/dev/null; then
        log_success "Installed kubernetes client"
    else
        log_warning "Failed to install kubernetes client (E2E tests may not work)"
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    local missing=()
    
    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        missing+=("pytest")
    fi
    
    # Check prometheus_client
    if ! python3 -c "import prometheus_client" 2>/dev/null; then
        missing+=("prometheus-client")
    fi
    
    # Check yaml
    if ! python3 -c "import yaml" 2>/dev/null; then
        missing+=("pyyaml")
    fi
    
    if [ ${#missing[@]} -eq 0 ]; then
        log_success "All required packages are installed"
        return 0
    else
        log_warning "Some packages may be missing: ${missing[*]}"
        log_info "You may need to install them manually or use a virtual environment"
        return 1
    fi
}

# Main
main() {
    echo "=========================================="
    echo "Installing Test Prerequisites"
    echo "=========================================="
    echo ""
    
    check_pip
    install_packages
    verify_installation
    
    echo ""
    log_success "Prerequisites installation completed!"
    echo ""
    echo "You can now run tests:"
    echo "  python3 tests/run_all_tests.py"
}

main "$@"

