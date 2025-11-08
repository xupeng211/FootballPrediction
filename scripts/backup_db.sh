#!/bin/bash

# Database Backup Script for Football Prediction System
# Author: Claude Code
# Version: 1.0
# Purpose: Automated database backup with compression and verification

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/football-prediction}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
COMPRESSION="${COMPRESSION:-gzip}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message"
}

log_info() { log "INFO" "$@"; }
log_success() { log -e "${GREEN}[SUCCESS]${NC} "$@"; }
log_warning() { log -e "${YELLOW}[WARNING]${NC} "$@"; }
log_error() { log -e "${RED}[ERROR]${NC} "$@"; }

# Load environment variables
load_env() {
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        source "$PROJECT_DIR/.env"
    elif [[ -f "$PROJECT_DIR/.env.production" ]]; then
        source "$PROJECT_DIR/.env.production"
    else
        log_error "Environment file not found"
        exit 1
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."

    # Check required variables
    local required_vars=("DATABASE_URL")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done

    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/database"
    mkdir -p "$BACKUP_DIR/logs"

    # Set proper permissions
    chmod 750 "$BACKUP_DIR"
    chmod 750 "$BACKUP_DIR/database"
    chmod 750 "$BACKUP_DIR/logs"

    log_success "Configuration validation completed"
}

# Extract database connection details
extract_db_config() {
    log_info "Extracting database configuration..."

    # Parse DATABASE_URL
    if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASSWORD="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"
    else
        log_error "Invalid DATABASE_URL format"
        exit 1
    fi

    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
}

# Create database backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/database/football_prediction_${timestamp}.sql"
    local compressed_file="$backup_file.$COMPRESSION"

    log_info "Creating database backup: $backup_file"

    # Use pg_dump for backup
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --lock-wait-timeout=30000 \
        --exclude-table-data='logs.*' \
        --file="$backup_file" \
        > "$BACKUP_DIR/logs/backup_${timestamp}.log" 2>&1

    local backup_result=$?

    if [[ $backup_result -eq 0 ]]; then
        log_success "Database backup created successfully"

        # Get backup file size
        local backup_size=$(du -h "$backup_file" | cut -f1)
        log_info "Backup size: $backup_size"

        # Compress the backup
        case "$COMPRESSION" in
            "gzip")
                gzip "$backup_file"
                ;;
            "bzip2")
                bzip2 "$backup_file"
                ;;
            "xz")
                xz "$backup_file"
                ;;
        esac

        # Get compressed size
        if [[ -f "$compressed_file" ]]; then
            local compressed_size=$(du -h "$compressed_file" | cut -f1)
            log_info "Compressed size: $compressed_size"
        fi

        # Create backup metadata
        create_backup_metadata "$timestamp" "$backup_file.$COMPRESSION"

    else
        log_error "Database backup failed"
        tail -20 "$BACKUP_DIR/logs/backup_${timestamp}.log"
        exit 1
    fi
}

# Create backup metadata
create_backup_metadata() {
    local timestamp="$1"
    local backup_file="$2"
    local metadata_file="$BACKUP_DIR/database/backup_metadata_${timestamp}.json"

    log_info "Creating backup metadata: $metadata_file"

    # Get database stats
    local db_stats=$(PGPASSWORD="$DB_PASSWORD" psql \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --no-password \
        -t \
        -c "SELECT
            pg_size_pretty(pg_database_size('$DB_NAME')) as db_size,
            (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count,
            (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public') as column_count;" \
        2>/dev/null || echo "0")

    local backup_size="0"
    if [[ -f "$backup_file" ]]; then
        backup_size=$(stat -c%s "$backup_file")
    fi

    # Create metadata JSON
    cat > "$metadata_file" << EOF
{
    "backup_id": "${timestamp}",
    "timestamp": "$(date -Iseconds)",
    "database": {
        "name": "$DB_NAME",
        "host": "$DB_HOST",
        "port": "$DB_PORT",
        "user": "$DB_USER",
        "size": "$db_stats"
    },
    "backup": {
        "file": "$backup_file",
        "size_bytes": $backup_size,
        "compression": "$COMPRESSION",
        "status": "completed"
    },
    "system": {
        "hostname": "$(hostname)",
        "user": "$(whoami)",
        "script_version": "1.0"
    }
}
EOF

    log_success "Backup metadata created"
}

# Verify backup integrity
verify_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_pattern="$BACKUP_DIR/database/football_prediction_*.sql.$COMPRESSION"
    local latest_backup=$(ls -t $backup_pattern | head -1)

    if [[ -z "$latest_backup" ]]; then
        log_error "No backup file found to verify"
        return 1
    fi

    log_info "Verifying backup: $latest_backup"

    # Test backup file integrity
    case "$COMPRESSION" in
        "gzip")
            if gzip -t "$latest_backup"; then
                log_success "Backup file integrity verified (gzip)"
            else
                log_error "Backup file integrity check failed (gzip)"
                return 1
            fi
            ;;
        "bzip2")
            if bzip2 -t "$latest_backup"; then
                log_success "Backup file integrity verified (bzip2)"
            else
                log_error "Backup file integrity check failed (bzip2)"
                return 1
            fi
            ;;
        "xz")
            if xz -t "$latest_backup"; then
                log_success "Backup file integrity verified (xz)"
            else
                log_error "Backup file integrity check failed (xz)"
                return 1
            fi
            ;;
    esac

    # Optional: Test restore (commented out for safety)
    # log_info "Testing backup restore..."
    # test_restore "$latest_backup"
}

# Test backup restore
test_restore() {
    local backup_file="$1"
    local test_db="test_restore_$(date +%s)"
    local temp_log="/tmp/test_restore_$(date +%s).log"

    log_info "Testing restore to database: $test_db"

    # Create test database
    PGPASSWORD="$DB_PASSWORD" createdb \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        "$test_db" \
        2>"$temp_log" || {
        log_error "Failed to create test database"
        cat "$temp_log"
        return 1
    }

    # Restore backup
    case "$COMPRESSION" in
        "gzip")
            gunzip -c "$backup_file" | PGPASSWORD="$DB_PASSWORD" pg_restore \
                --host="$DB_HOST" \
                --port="$DB_PORT" \
                --username="$DB_USER" \
                --dbname="$test_db" \
                --verbose \
                --no-password \
                2>>"$temp_log"
            ;;
        "bzip2")
            bunzip2 -c "$backup_file" | PGPASSWORD="$DB_PASSWORD" pg_restore \
                --host="$DB_HOST" \
                --port="$DB_PORT" \
                --username="$DB_USER" \
                --dbname="$test_db" \
                --verbose \
                --no-password \
                2>>"$temp_log"
            ;;
        "xz")
            unxz -c "$backup_file" | PGPASSWORD="$DB_PASSWORD" pg_restore \
                --host="$DB_HOST" \
                --port="$DB_PORT" \
                --username="$DB_USER" \
                --dbname="$test_db" \
                --verbose \
                --no-password \
                2>>"$temp_log"
            ;;
    esac

    local restore_result=$?

    # Clean up test database
    PGPASSWORD="$DB_PASSWORD" dropdb \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        "$test_db" \
        2>/dev/null || true

    if [[ $restore_result -eq 0 ]]; then
        log_success "Backup restore test passed"
    else
        log_error "Backup restore test failed"
        tail -10 "$temp_log"
        return 1
    fi

    rm -f "$temp_log"
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."

    local deleted_count=0
    local total_size_freed=0

    # Find and delete old backup files
    while IFS= read -r -r file; do
        if [[ -f "$file" ]]; then
            local file_size=$(stat -c%s "$file")
            rm -f "$file"
            total_size_freed=$((total_size_freed + file_size))
            deleted_count=$((deleted_count + 1))
            log_info "Deleted old backup: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR/database" -name "football_prediction_*.sql.*" -type f -mtime +$RETENTION_DAYS)

    # Find and delete old metadata files
    while IFS= read -r -r file; do
        if [[ -f "$file" ]]; then
            rm -f "$file"
            log_info "Deleted old metadata: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR/database" -name "backup_metadata_*.json" -type f -mtime +$RETENTION_DAYS)

    # Convert bytes to human readable format
    local size_freed_gb=$((total_size_freed / 1024 / 1024 / 1024))
    local size_freed_mb=$(((total_size_freed / 1024 / 1024) % 1024))

    log_success "Cleanup completed: deleted $deleted_count files, freed ${size_freed_gb}GB ${size_freed_mb}MB"
}

# Create backup report
create_backup_report() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local report_file="$BACKUP_DIR/logs/backup_report_${timestamp}.txt"

    log_info "Creating backup report: $report_file"

    cat > "$report_file" << EOF
===========================================
Football Prediction System Backup Report
===========================================

Report Generated: $(date '+%Y-%m-%d %H:%M:%S')
Backup Directory: $BACKUP_DIR

Backup Statistics:
-------------------
Total Backups: $(find "$BACKUP_DIR/database" -name "football_prediction_*.sql.*" -type f | wc -l)
Total Size: $(du -sh "$BACKUP_DIR/database" | cut -f1)
Retention Period: $RETENTION_DAYS days
Compression: $COMPRESSION

Recent Backups:
----------------
$(ls -lh "$BACKUP_DIR/database/football_prediction_*.sql.*" | tail -5)

Disk Usage:
------------
Backup Directory: $(du -sh "$BACKUP_DIR" | cut -f1)
Available Space: $(df -h "$BACKUP_DIR" | awk 'NR==2 {print $4}')

Configuration:
-------------
Database: $DB_NAME@$DB_HOST:$DB_PORT
Backup User: $DB_USER
Compression: $COMPRESSION
Retention: $RETENTION_DAYS days

System Information:
-------------------
Hostname: $(hostname)
User: $(whoami)
OS: $(uname -s -r)
Memory: $(free -h | grep Mem)
Disk: $(df -h / | awk 'NR==2 {print $2 " used, " $4 " available"}')

===========================================
End of Report
===========================================
EOF

    log_success "Backup report created: $report_file"
}

# Send notification (optional)
send_notification() {
    local status="$1"
    local message="$2"

    if [[ -n "${WEBHOOK_URL:-}" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"Football Prediction Backup: $status\",
                \"message\": \"$message\",
                \"timestamp\": \"$(date -Iseconds)\"
            }" \
            2>/dev/null || log_warning "Failed to send webhook notification"
    fi

    if [[ -n "${EMAIL_TO:-}" && -n "${EMAIL_FROM:-}" ]]; then
        echo "$message" | mail -s "Football Prediction Backup: $status" "$EMAIL_TO" \
            2>/dev/null || log_warning "Failed to send email notification"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "🗄️ Football Prediction Database Backup"
    echo "=========================================="
    echo "Started at: $(date)"
    echo "Backup Directory: $BACKUP_DIR"
    echo ""

    # Load environment and validate
    load_env
    validate_config
    extract_db_config

    # Create backup
    local start_time=$(date +%s)
    create_backup
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Verify backup
    if verify_backup; then
        send_notification "SUCCESS" "Database backup completed successfully in ${duration}s"
        log_success "Database backup completed successfully in ${duration}s"
    else
        send_notification "FAILED" "Database backup verification failed"
        log_error "Database backup verification failed"
        exit 1
    fi

    # Clean up old backups
    cleanup_old_backups

    # Create report
    create_backup_report

    echo ""
    echo "=========================================="
    echo "✅ Database Backup Completed Successfully"
    echo "=========================================="
    echo "Duration: ${duration}s"
    echo "Next backup: $(date -d '+1 day' '+%Y-%m-%d %H:%M:%S')"
}

# Handle script arguments
case "${1:-}" in
    "verify")
        log_info "Running backup verification only..."
        load_env
        validate_config
        verify_backup
        ;;
    "cleanup")
        log_info "Running cleanup only..."
        load_env
        validate_config
        cleanup_old_backups
        ;;
    "test")
        log_info "Running backup test..."
        load_env
        validate_config
        extract_db_config
        create_backup
        verify_backup
        ;;
    *)
        main
        ;;
esac