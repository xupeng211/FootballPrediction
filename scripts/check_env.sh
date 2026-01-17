#!/bin/bash
# V41.152 Environment Self-Check Script
#
# This script performs comprehensive environment validation before
# running the Sentinel Orchestrator. It checks:
#   - Python version and dependencies
#   - Proxy connectivity and latency
#   - Database connectivity
#   - Disk space availability
#   - Directory structure integrity
#
# Usage:
#   ./scripts/check_env.sh [--verbose] [--fix]
#
# Exit Codes:
#   0 - All checks passed
#   1 - Critical checks failed
#   2 - Warnings only

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Thresholds
MIN_DISK_GB=1.0
MAX_PROXY_LATENCY_MS=5000
MIN_PYTHON_VERSION="3.11"

# Default proxy settings
PROXY_HOST="${PROXY_HOST:-172.25.16.1}"
PROXY_PORT="${PROXY_PORT:-7890}"

# ============================================================================
# Utilities
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

# ============================================================================
# Checks
# ============================================================================

check_python_version() {
    print_header "Python Version Check"

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found"
        return 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    log_info "Detected Python version: $PYTHON_VERSION"

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        log_error "Python $MIN_PYTHON_VERSION+ required, found $PYTHON_VERSION"
        return 1
    fi

    log_success "Python version OK: $PYTHON_VERSION"
    return 0
}

check_dependencies() {
    print_header "Python Dependencies Check"

    local missing_deps=()

    # Core dependencies
    local deps=(
        "psycopg2"
        "playwright"
        "bs4"
        "pydantic"
        "requests"
    )

    for dep in "${deps[@]}"; do
        if ! python3 -c "import ${dep}" 2>/dev/null; then
            missing_deps+=("$dep")
            log_error "Missing dependency: $dep"
        else
            log_success "Dependency OK: $dep"
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "Missing ${#missing_deps[@]} dependencies"
        log_info "Install with: pip install ${missing_deps[*]}"
        return 1
    fi

    return 0
}

check_proxy_connectivity() {
    print_header "Proxy Connectivity Check"

    log_info "Testing proxy: $PROXY_HOST:$PROXY_PORT"

    # Check if proxy is reachable
    local start_time=$(date +%s%3N)
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$PROXY_HOST/$PROXY_PORT" 2>/dev/null; then
        local end_time=$(date +%s%3N)
        local latency=$((end_time - start_time))

        log_success "Proxy reachable: ${latency}ms latency"

        if [ $latency -gt $MAX_PROXY_LATENCY_MS ]; then
            log_warning "High latency: ${latency}ms (threshold: ${MAX_PROXY_LATENCY_MS}ms)"
            return 2
        fi

        return 0
    else
        log_error "Proxy unreachable: $PROXY_HOST:$PROXY_PORT"
        return 1
    fi
}

check_database_connectivity() {
    print_header "Database Connectivity Check"

    # Load database settings from Python
    local db_check=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from src.config_unified import get_settings
try:
    settings = get_settings()
    print(f'{settings.database.host}|{settings.database.port}|{settings.database.name}|{settings.database.user}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)

    if [[ $db_check == ERROR* ]]; then
        log_error "Failed to load database configuration"
        return 1
    fi

    IFS='|' read -r db_host db_port db_name db_user <<< "$db_check"

    log_info "Testing database: $db_host:$db_port/$db_name"

    if PGPASSWORD="$DB_PASSWORD" psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "SELECT 1;" &> /dev/null; then
        log_success "Database connection OK"
        return 0
    else
        log_error "Database connection failed"
        return 1
    fi
}

check_disk_space() {
    print_header "Disk Space Check"

    local storage_dir="$PROJECT_ROOT/storage"

    if [ ! -d "$storage_dir" ]; then
        mkdir -p "$storage_dir"
    fi

    # Get disk space in GB
    local free_space=$(df -BG "$storage_dir" | awk 'NR==2 {print $4}' | tr -d 'G')

    log_info "Available disk space: ${free_space}GB"

    if (( $(echo "$free_space < $MIN_DISK_GB" | bc -l) )); then
        log_error "Insufficient disk space: ${free_space}GB (required: ${MIN_DISK_GB}GB)"
        return 1
    fi

    log_success "Disk space OK: ${free_space}GB available"
    return 0
}

check_directory_structure() {
    print_header "Directory Structure Check"

    local required_dirs=(
        "storage/html_vault"
        "storage/injection_queue"
        "logs"
        "config"
    )

    local missing_dirs=()

    for dir in "${required_dirs[@]}"; do
        local full_path="$PROJECT_ROOT/$dir"
        if [ ! -d "$full_path" ]; then
            missing_dirs+=("$dir")
            log_warning "Missing directory: $dir"
        else
            log_success "Directory OK: $dir"
        fi
    done

    if [ ${#missing_dirs[@]} -gt 0 ]; then
        log_info "Creating missing directories..."

        for dir in "${missing_dirs[@]}"; do
            mkdir -p "$PROJECT_ROOT/$dir"
            log_success "Created: $dir"
        done
    fi

    return 0
}

check_playwright_browsers() {
    print_header "Playwright Browsers Check"

    if ! python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().start().stop()" 2>/dev/null; then
        log_error "Playwright browsers not installed"

        if [ "${1:-}" == "--fix" ]; then
            log_info "Installing Playwright browsers..."
            playwright install chromium
            return $?
        else
            log_info "Install with: playwright install chromium"
            return 1
        fi
    fi

    log_success "Playwright browsers OK"
    return 0
}

check_environment_variables() {
    print_header "Environment Variables Check"

    local required_vars=(
        "DB_PASSWORD"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_warning "Not set: $var"
        else
            # Mask the value for display
            local value="${!var}"
            local masked="${value:0:3}***"
            log_success "Set: $var=$masked"
        fi
    done

    return 0
}

# ============================================================================
# Main
# ============================================================================

main() {
    local verbose=false
    local fix=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                verbose=true
                shift
                ;;
            --fix)
                fix=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--verbose] [--fix]"
                exit 1
                ;;
        esac
    done

    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║   V41.152 Environment Self-Check      ║"
    echo "║   Sentinel Orchestrator Pre-Flight    ║"
    echo "╚════════════════════════════════════════╝"
    echo ""

    local exit_code=0
    local critical_failures=0
    local warnings=0

    # Run all checks
    check_python_version || ((critical_failures++))
    check_dependencies || ((critical_failures++))
    check_proxy_connectivity || ((critical_failures++))
    check_database_connectivity || ((critical_failures++))
    check_disk_space || ((critical_failures++))
    check_directory_structure || ((warnings++))
    check_playwright_browsers --fix || ((critical_failures++))
    check_environment_variables || ((warnings++))

    # Summary
    print_header "Check Summary"

    if [ $critical_failures -eq 0 ]; then
        log_success "All critical checks passed!"
    else
        log_error "$critical_failures critical check(s) failed"
        exit_code=1
    fi

    if [ $warnings -gt 0 ]; then
        log_warning "$warnings warning(s) issued"
        [ $exit_code -eq 0 ] && exit_code=2
    fi

    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "🟢 Environment is ready for Sentinel Orchestrator"
    elif [ $exit_code -eq 1 ]; then
        echo "🔴 Critical issues detected. Please fix before running."
    else
        echo "🟡 Warnings detected. System can run but may have issues."
    fi
    echo ""

    return $exit_code
}

# Run main
main "$@"
