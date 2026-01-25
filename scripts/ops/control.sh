#!/bin/bash
#
# V70.300 - Football Prediction Control Center
# ============================================
#
# One-Click Control Center for the Football Prediction System
# Integrates V66-V70 full-stack functionality into standardized operations
#
# @file control.sh
# @version V70.300
# @since 2026-01-25
#
# Usage:
#   ./control.sh start     - Start orchestrator as daemon
#   ./control.sh status    - Show dashboard and health score
#   ./control.sh stop      - Gracefully shutdown all services
#   ./control.sh repair    - Reset FAILED records for retry
#   ./control.sh logs      - Show recent logs
#   ./control.sh restart   - Restart orchestrator
#   ./control.sh help      - Show this message
#
# ============================================================================

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Node.js executable
NODE_BIN="${NODE_BIN:-node}"

# PID file
PID_DIR="${PROJECT_ROOT}/var/run"
PID_FILE="${PID_DIR}/orchestrator.pid"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/orchestrator.log"

# Orchestrator
ORCHESTRATOR="${PROJECT_ROOT}/src/ops/v69_000_pipeline_orchestrator.js"
SENTINEL="${PROJECT_ROOT}/src/ops/v70_200_data_sentinel.js"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Ensure directories exist
ensure_dirs() {
    mkdir -p "${PID_DIR}"
    mkdir -p "${LOG_DIR}"

    # V72.100: Fix log directory permissions for write access
    chmod 777 "${LOG_DIR}" 2>/dev/null || true

    # V72.100: Ensure log file is writable (create/truncate if needed)
    if [[ -f "${LOG_FILE}" ]]; then
        chmod 644 "${LOG_FILE}" 2>/dev/null || true
    fi

    # V72.100: Load environment variables from .env
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        set -a
        source "${PROJECT_ROOT}/.env"
        set +a
    fi
}

# Check if orchestrator is running
is_running() {
    if [[ -f "${PID_FILE}" ]]; then
        local pid=$(cat "${PID_FILE}")
        if ps -p "${pid}" > /dev/null 2>&1; then
            return 0
        else
            # Stale PID file
            rm -f "${PID_FILE}"
            return 1
        fi
    fi
    return 1
}

# Wait for process to stop
wait_for_stop() {
    local pid=$1
    local max_wait=30
    local waited=0

    while ps -p "${pid}" > /dev/null 2>&1; do
        if [[ ${waited} -ge ${max_wait} ]]; then
            log_warning "Process did not stop gracefully, forcing..."
            kill -9 "${pid}" 2>/dev/null || true
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done
}

# ============================================================================
# COMMAND: START (V72.100 Enhanced with --limit option for pilot testing)
# ============================================================================

cmd_start() {
    local limit=""
    local daemon_mode=true

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --limit)
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    limit="$2"
                    daemon_mode=false  # Run in foreground for pilot testing
                    shift 2
                else
                    log_error "Invalid value for --limit. Must be a number."
                    return 1
                fi
                ;;
            *)
                shift
                ;;
        esac
    done

    log_info "Starting Football Prediction Orchestrator..."
    if [[ -n "$limit" ]]; then
        log_info "Pilot mode: Processing $limit matches (non-daemon)"
    fi

    ensure_dirs

    if is_running; then
        log_warning "Orchestrator is already running (PID: $(cat ${PID_FILE}))"
        return 0
    fi

    # Check if orchestrator file exists
    if [[ ! -f "${ORCHESTRATOR}" ]]; then
        log_error "Orchestrator not found: ${ORCHESTRATOR}"
        return 1
    fi

    # Start orchestrator
    cd "${PROJECT_ROOT}"

    if [[ "$daemon_mode" == true ]]; then
        # Daemon mode (background)
        log_info "Starting in daemon mode..."
        nohup "${NODE_BIN}" "${ORCHESTRATOR}" daemon \
            > "${LOG_FILE}" 2>&1 &

        local pid=$!
        echo ${pid} > "${PID_FILE}"

        # Wait a bit and check if it's still running
        sleep 2
        if ps -p "${pid}" > /dev/null 2>&1; then
            log_success "Orchestrator started (PID: ${pid})"
            log_info "Logs: ${LOG_FILE}"
            return 0
        else
            log_error "Orchestrator failed to start. Check logs: ${LOG_FILE}"
            rm -f "${PID_FILE}"
            return 1
        fi
    else
        # V72.100: Pilot mode (foreground, limited run)
        log_info "Starting in pilot mode (foreground, ${limit} matches)..."
        "${NODE_BIN}" "${ORCHESTRATOR}" daemon --limit "$limit" \
            2>&1 | tee -a "${LOG_FILE}"
        return ${PIPESTATUS[0]}
    fi
}

# ============================================================================
# COMMAND: STATUS
# ============================================================================

cmd_status() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║          Football Prediction System - Control Center Status                 ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    # Check if orchestrator is running
    if is_running; then
        local pid=$(cat "${PID_FILE}")
        log_success "Orchestrator is running (PID: ${pid})"

        # Show process info
        echo ""
        echo "Process Information:"
        ps -p "${pid}" -o pid,etime,%cpu,%mem,command || true
        echo ""
    else
        log_warning "Orchestrator is NOT running"
    fi

    # Run sentinel scan
    echo ""
    log_info "Running V70.200 Data Sentinel..."
    echo ""

    cd "${PROJECT_ROOT}"
    "${NODE_BIN}" "${SENTINEL}" scan 2>&1

    return $?
}

# ============================================================================
# COMMAND: STOP
# ============================================================================

cmd_stop() {
    log_info "Stopping Football Prediction Orchestrator..."

    if ! is_running; then
        log_warning "Orchestrator is not running"
        return 0
    fi

    local pid=$(cat "${PID_FILE}")

    # Try graceful shutdown first
    log_info "Sending SIGTERM to process ${pid}..."
    kill -TERM "${pid}" 2>/dev/null || true

    wait_for_stop "${pid}"

    if ps -p "${pid}" > /dev/null 2>&1; then
        log_error "Failed to stop process ${pid}"
        return 1
    else
        rm -f "${PID_FILE}"
        log_success "Orchestrator stopped"

        # Additional cleanup: kill any stray browser processes
        log_info "Cleaning up browser processes..."
        pkill -f "playwright" 2>/dev/null || true
        pkill -f "chromium" 2>/dev/null || true

        return 0
    fi
}

# ============================================================================
# COMMAND: RESTART
# ============================================================================

cmd_restart() {
    log_info "Restarting Football Prediction Orchestrator..."

    cmd_stop
    sleep 2
    cmd_start

    return $?
}

# ============================================================================
# COMMAND: REPAIR (V71.100 Enhanced)
# ============================================================================

cmd_repair() {
    local failed_only=false
    local cleanup_temp=false

    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --failed-only)
                failed_only=true
                shift
                ;;
            --cleanup-temp)
                cleanup_temp=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    log_info "Repairing FAILED records..."
    if [[ "$failed_only" == true ]]; then
        log_info "Mode: --failed-only (only repair FAILED records)"
    fi
    if [[ "$cleanup_temp" == true ]]; then
        log_info "Mode: --cleanup-temp (cleanup residual temp files)"
    fi

    cd "${PROJECT_ROOT}"

    # Step 1: Cleanup temp files from FAILED records
    if [[ "$cleanup_temp" == true ]]; then
        log_info "Cleaning up residual temp files from FAILED records..."

        # Find and remove temp files older than 1 hour
        find /tmp -name "football_*" -mtime +1/24 -type f -delete 2>/dev/null || true
        find "${LOG_DIR}" -name "*.tmp" -mtime +1 -type f -delete 2>/dev/null || true

        # Cleanup Python cache
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true

        log_success "Temp file cleanup completed"
    fi

    # Step 2: Create repair SQL script
    local temp_sql="/tmp/repair_failed_v71_100_$$.sql"

    cat > "$temp_sql" << 'EOF'
-- V71.100: Repair FAILED records (Enhanced)
-- Reset FAILED records to previous valid state for retry
-- Supports targeted repair with filtering options

BEGIN;

-- Show count before repair
SELECT 'BEFORE REPAIR' as stage, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;

EOF

    if [[ "$failed_only" == true ]]; then
        # Only repair FAILED records (no smart state restoration)
        cat >> "$temp_sql" << 'EOF'
-- V71.100: Simple reset FAILED -> DISCOVERED (for retry from scratch)
UPDATE match_pipeline_state
SET status = 'DISCOVERED',
    updated_at = NOW(),
    retry_count = COALESCE(retry_count, 0) + 1,
    error_message = NULL
WHERE status = 'FAILED';
EOF
    else
        # Smart repair: restore to previous valid state
        cat >> "$temp_sql" << 'EOF'
-- Repair: FAILED -> MAPPED (for odds harvest failures)
UPDATE match_pipeline_state
SET status = 'MAPPED', updated_at = NOW()
WHERE status = 'FAILED'
  AND match_id IN (
      SELECT mm.fotmob_id
      FROM matches_mapping mm
      WHERE mm.fotmob_id = match_pipeline_state.match_id
        AND mm.oddsportal_url IS NOT NULL
  );

-- Repair: FAILED -> ENRICHED (for bridge mapping failures)
UPDATE match_pipeline_state
SET status = 'ENRICHED', updated_at = NOW()
WHERE status = 'FAILED'
  AND match_id IN (
      SELECT match_id
      FROM matches
      WHERE match_id = match_pipeline_state.match_id
        AND l2_raw_json IS NOT NULL
  );

-- Repair: FAILED -> DISCOVERED (for L2 enrichment failures)
UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW()
WHERE status = 'FAILED';
EOF
    fi

    cat >> "$temp_sql" << 'EOF'

COMMIT;

-- Show count after repair
SELECT 'AFTER REPAIR' as stage, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;

-- Show failed records by reason (if any)
SELECT
    SUBSTRING(error_message FROM 1 FOR 50) as error_reason,
    COUNT(*) as failed_count
FROM match_pipeline_state
WHERE status = 'FAILED' AND error_message IS NOT NULL
GROUP BY error_reason
ORDER BY failed_count DESC
LIMIT 10;
EOF

    # Run repair SQL
    if command -v docker > /dev/null 2>&1; then
        # Using Docker
        docker exec -i football_db psql -U football_user -d football_db < "$temp_sql"
    else
        # Direct connection
        psql -h 172.25.16.1 -U football_user -d football_db < "$temp_sql"
    fi

    local repaired=$?

    rm -f "$temp_sql"

    if [[ ${repaired} -eq 0 ]]; then
        log_success "Repair completed successfully"

        # Show repair summary
        if [[ "$failed_only" == true ]]; then
            echo ""
            log_info "Records reset to DISCOVERED for retry"
        fi
        return 0
    else
        log_error "Repair failed. Check database connection."
        return 1
    fi
}

# ============================================================================
# COMMAND: LOGS
# ============================================================================

cmd_logs() {
    local lines=${1:-50}

    if [[ -f "${LOG_FILE}" ]]; then
        tail -n "${lines}" "${LOG_FILE}"
    else
        log_warning "Log file not found: ${LOG_FILE}"
    fi
}

# ============================================================================
# COMMAND: HEALTH
# ============================================================================

cmd_health() {
    cd "${PROJECT_ROOT}"

    log_info "Running health check..."
    echo ""

    # Quick health check (JSON output)
    "${NODE_BIN}" "${SENTINEL}" json 2>&1 | jq -r '
        {
            "health_score": .healthScore,
            "progress": .completeness.progress_percent,
            "corrupted": .anomalies.total_corrupted,
            "mph": .throughput.mph,
            "eta": .throughput.eta_date
        } | to_entries | map("\(.key): \(.value)") | join("\n")
    ' || log_error "Health check failed"

    return $?
}

# ============================================================================
# COMMAND: BACKUP
# ============================================================================

cmd_backup() {
    log_info "Creating database backup..."

    local backup_dir="${PROJECT_ROOT}/data/backups"
    mkdir -p "${backup_dir}"

    local backup_file="${backup_dir}/football_db_$(date +%Y%m%d_%H%M%S).sql"

    if command -v docker > /dev/null 2>&1; then
        docker exec football_db pg_dump -U football_user football_db > "${backup_file}"
    else
        pg_dump -h 172.25.16.1 -U football_user football_db > "${backup_file}"
    fi

    if [[ $? -eq 0 ]]; then
        log_success "Backup created: ${backup_file}"

        # Compress backup
        gzip "${backup_file}"
        log_success "Backup compressed: ${backup_file}.gz"

        return 0
    else
        log_error "Backup failed"
        return 1
    fi
}

# ============================================================================
# COMMAND: CLEAN
# ============================================================================

cmd_clean() {
    log_info "Cleaning old logs and temporary files..."

    # Remove logs older than 7 days
    find "${LOG_DIR}" -name "*.log" -mtime +7 -delete 2>/dev/null || true

    # Remove old backups (keep last 5)
    find "${PROJECT_ROOT}/data/backups" -name "*.sql.gz" -type f | sort | head -n -5 | xargs rm -f 2>/dev/null || true

    log_success "Cleanup completed"

    return 0
}

# ============================================================================
# COMMAND: HELP
# ============================================================================

cmd_help() {
    cat << EOF
Football Prediction System - Control Center (V71.100)
=====================================================

Usage: ./control.sh <command> [options]

Commands:
  start       Start orchestrator as daemon
  stop        Stop orchestrator gracefully
  restart     Restart orchestrator
  status      Show system status and health dashboard
  health      Quick health check (JSON format)
  repair      Reset FAILED records for retry
  logs [N]    Show last N lines of logs (default: 50)
  backup      Create database backup
  clean       Clean old logs and temporary files
  help        Show this message

Repair Options:
  --failed-only       Only repair FAILED records (reset to DISCOVERED)
  --cleanup-temp      Clean residual temp files from FAILED records

Examples:
  ./control.sh start                          # Start the system
  ./control.sh status                         # Check status
  ./control.sh repair --failed-only          # Repair only FAILED records
  ./control.sh repair --cleanup-temp          # Repair with temp cleanup
  ./control.sh logs 100                        # Show last 100 log lines

For detailed operations, see: docs/OPERATIONS_MANUAL.md
EOF
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    local command=${1:-help}

    case "${command}" in
        start)
            shift  # Remove 'start' from arguments
            cmd_start "$@"
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        health)
            cmd_health
            ;;
        repair)
            shift  # Remove 'repair' from arguments
            cmd_repair "$@"
            ;;
        logs)
            cmd_logs "${2:-50}"
            ;;
        backup)
            cmd_backup
            ;;
        clean)
            cmd_clean
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log_error "Unknown command: ${command}"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
