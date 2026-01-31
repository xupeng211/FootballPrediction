#!/bin/bash
###############################################################################
# V43.300 One-Click Production Deployment Script
# ============================================
#
# Automated deployment script for temporal-sync-engine with PM2 supervision
#
# Features:
#   - Environment validation
#   - Dependency installation
#   - Pre-deployment testing
#   - Service orchestration (start/reload/save)
#   - Startup configuration
#
# Usage:
#   ./scripts/ops/deploy.sh [environment]
#
# Environment:
#   - production (default): Production deployment
#   - development: Development deployment
#
# Author: Lead Systems Reliability Engineer (SRE)
# Version: V43.300
# Date: 2026-01-24
###############################################################################

set -e  # Exit on any error

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

# Environment selection
ENVIRONMENT="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [deploy]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [deploy]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [deploy]${NC} $1"
}

# ============================================================================
# ENVIRONMENT SELF-CHECK
# ============================================================================

step_environment_check() {
    log_info "=== ENVIRONMENT SELF-CHECK ==="

    # Change to project root
    cd "$PROJECT_ROOT"

    # Check .env file exists
    if [ ! -f ".env" ]; then
        log_error ".env file not found. Please create .env file with database credentials."
        log_info ""
        log_info "Example .env file:"
        log_info "  DB_HOST=172.25.16.1"
        log_info "  DB_PORT=5432"
        log_info "  DB_NAME=football_db"
        log_info "  DB_USER=football_user"
        log_info "  DB_PASSWORD=football_pass"
        exit 1
    fi

    log_info ".env file found"
    log_info "Environment: $ENVIRONMENT"
    log_info "Project root: $PROJECT_ROOT"
    log_info ""
}

# ============================================================================
# DEPENDENCY INSTALLATION
# ============================================================================

step_install_dependencies() {
    log_info "=== DEPENDENCY INSTALLATION ==="

    cd "$PROJECT_ROOT"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing dependencies..."
        npm install
    else
        log_info "Dependencies already installed (node_modules exists)"
    fi

    log_info "Installation complete"
    log_info ""
}

# ============================================================================
# ADMISSION TEST
# ============================================================================

step_admission_test() {
    log_info "=== ADMISSION TEST ==="

    cd "$PROJECT_ROOT/scripts/ops"

    # Run unit tests
    log_info "Running unit tests..."
    if ! npm test; then
        log_error "Admission test failed. Unit tests did not pass."
        log_error "Deployment aborted."
        exit 1
    fi

    log_info "Admission test: PASSED"
    log_info ""
}

# ============================================================================
# LOG DIRECTORY SETUP
# ============================================================================

step_setup_logs() {
    log_info "=== LOG DIRECTORY SETUP ==="

    mkdir -p "$LOG_DIR"

    log_info "Log directory: $LOG_DIR"
    log_info ""
}

# ============================================================================
# PM2 SERVICE ORCHESTRATION
# ============================================================================

step_orchestrate_service() {
    log_info "=== PM2 SERVICE ORCHESTRATION ==="

    cd "$PROJECT_ROOT"

    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
        log_warn "PM2 not found. Installing..."
        npm install -g pm2
        log_info "PM2 installed successfully"
    fi

    # Check if service exists
    if pm2 list | grep -q "temporal-sync-engine.*online"; then
        log_info "Service 'temporal-sync-engine' is running, reloading..."
        if ! pm2 reload ecosystem.config.js --env "$ENVIRONMENT" > /dev/null 2>&1; then
            log_warn "Reload failed (service may not be running), attempting start..."
            pm2 start ecosystem.config.js --env "$ENVIRONMENT"
        else
            log_info "Service reloaded successfully"
        fi
    else
        log_info "Service 'temporal-sync-engine' is not running, starting..."
        pm2 start ecosystem.config.js --env "$ENVIRONMENT"
    fi

    # Save PM2 process list
    log_info "Saving PM2 process list..."
    pm2 save

    # Setup startup script
    log_info "Configuring PM2 startup script..."
    pm2 startup || log_warn "PM2 startup command not available (systemd not detected)"

    log_info "Service orchestration complete"
    log_info ""
}

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

step_deployment_summary() {
    log_info "=== DEPLOYMENT SUMMARY ==="
    log_info ""

    # Show PM2 status
    log_info "PM2 Process List:"
    pm2 list

    log_info ""
    log_info "Service Management Commands:"
    log_info "  Logs:     pm2 logs temporal-sync-engine"
    log_info "  Status:   pm2 status"
    log_info "  Restart:  pm2 restart temporal-sync-engine"
    log_info "  Stop:     pm2 stop temporal-sync-engine"
    log_info "  Reload:   pm2 reload ecosystem.config.js"
    log_info ""
}

# ============================================================================
# MAIN DEPLOYMENT FLOW
# ============================================================================

main() {
    echo ""
    echo "==========================================="
    echo "V43.300 Production Deployment"
    echo "==========================================="
    echo ""
    echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [deploy] Deployment starting..."
    echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [deploy] Environment: $ENVIRONMENT"
    echo ""

    # Execute deployment steps
    step_environment_check
    step_install_dependencies
    step_setup_logs
    step_admission_test
    step_orchestrate_service

    # Deployment summary
    step_deployment_summary

    echo "==========================================="
    echo "[V43.300] Deployment successful. Service 'temporal-sync-engine' is now supervised by PM2."
    echo "==========================================="
    echo ""

    return 0
}

# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --help|-h)
            echo "Usage: $0 [environment]"
            echo ""
            echo "Arguments:"
            echo "  environment    Target environment (default: production)"
            echo ""
            echo "Examples:"
            echo "  $0              # Deploy to production"
            echo "  $0 development  # Deploy to development"
            echo ""
            exit 0
            ;;
        *)
            break
            ;;
    esac
    shift
done

# Run main deployment flow
main "$@"
