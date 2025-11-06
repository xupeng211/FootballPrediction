#!/bin/bash

# Database Restore Script for Football Prediction System
# Author: Claude Code
# Version: 1.0
# Purpose: Automated database restore with validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/football-prediction}"

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

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_FILE

Options:
    -h, --help              Show this help message
    -d, --database NAME      Target database name (default: football_prediction)
    -u, --user USER          Database user (default: from .env)
    -H, --host HOST          Database host (default: from .env)
    -p, --port PORT          Database port (default: from .env)
    --dry-run               Show what would be done without executing
    --verify                Verify backup integrity before restore
    --force                 Force restore even if database exists
    --backup-existing       Backup existing database before restore

Arguments:
    BACKUP_FILE              Path to backup file (.sql, .sql.gz, .sql.bz2, .sql.xz)

Examples:
    $0 /opt/backups/football-prediction/database/football_prediction_20251106_120000.sql.gz
    $0 --database test_db --verify football_prediction_20251106_120000.sql
    $0 --dry-run --backup-existing /path/to/backup.sql.gz

EOF
}

# Parse command line arguments
DATABASE_NAME=""
DATABASE_USER=""
DATABASE_HOST=""
DATABASE_PORT=""
DRY_RUN=false
VERIFY_BACKUP=false
FORCE_RESTORE=false
BACKUP_EXISTING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -d|--database)
            DATABASE_NAME="$2"
            shift 2
            ;;
        -u|--user)
            DATABASE_USER="$2"
            shift 2
            ;;
        -H|--host)
            DATABASE_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DATABASE_PORT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verify)
            VERIFY_BACKUP=true
            shift
            ;;
        --force)
            FORCE_RESTORE=true
            shift
            ;;
        --backup-existing)
            BACKUP_EXISTING=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "${BACKUP_FILE:-}" ]]; then
                BACKUP_FILE="$1"
            else
                log_error "Multiple backup files specified"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [[ -z "${BACKUP_FILE:-}" ]]; then
    log_error "Backup file is required"
    show_usage
    exit 1
fi

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

    # Use command line overrides or environment defaults
    DATABASE_NAME="${DATABASE_NAME:-${DB_NAME:-football_prediction}"
    DATABASE_USER="${DATABASE_USER:-${DB_USER:-postgres}}"
    DATABASE_HOST="${DATABASE_HOST:-${DB_HOST:-localhost}}"
    DATABASE_PORT="${DATABASE_PORT:-${DB_PORT:-5432}}"
}

# Validate backup file
validate_backup_file() {
    log_info "Validating backup file: $BACKUP_FILE"

    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "Backup file does not exist: $BACKUP_FILE"
        exit 1
    fi

    # Check file extension
    local file_extension="${BACKUP_FILE##*.}"
    case "$file_extension" in
        "sql")
            BACKUP_FORMAT="plain"
            ;;
        "gz")
            BACKUP_FORMAT="gzip"
            ;;
        "bz2")
            BACKUP_FORMAT="bzip2"
            ;;
        "xz")
            BACKUP_FORMAT="xz"
            ;;
        *)
            log_error "Unsupported backup format: $file_extension"
            exit 1
            ;;
    esac

    log_info "Backup format: $BACKUP_FORMAT"

    # Check file size
    local file_size=$(stat -c%s "$BACKUP_FILE")
    if [[ $file_size -eq 0 ]]; then
        log_error "Backup file is empty"
        exit 1
    fi

    local file_size_human=$(numfmt --to=iec-i --suffix=B "$file_size")
    log_info "Backup file size: $file_size_human"

    # Verify file integrity if requested
    if [[ "$VERIFY_BACKUP" == "true" ]]; then
        verify_backup_integrity
    fi
}

# Verify backup integrity
verify_backup_integrity() {
    log_info "Verifying backup integrity..."

    case "$BACKUP_FORMAT" in
        "gzip")
            if gzip -t "$BACKUP_FILE"; then
                log_success "Backup integrity verified (gzip)"
            else
                log_error "Backup integrity check failed (gzip)"
                exit 1
            fi
            ;;
        "bzip2")
            if bzip2 -t "$BACKUP_FILE"; then
                log_success "Backup integrity verified (bzip2)"
            else
                log_error "Backup integrity check failed (bzip2)"
                exit 1
            fi
            ;;
        "xz")
            if xz -t "$BACKUP_FILE"; then
                log_success "Backup integrity verified (xz)"
            else
                log_error "Backup integrity check failed (xz)"
                exit 1
            fi
            ;;
        "sql")
            # For plain SQL files, check if it's a valid SQL dump
            if head -n 1 "$BACKUP_FILE" | grep -q "PostgreSQL database dump"; then
                log_success "Backup integrity verified (PostgreSQL dump)"
            else
                log_warning "Backup file may not be a PostgreSQL dump"
            fi
            ;;
    esac
}

# Check database connection
check_database_connection() {
    log_info "Testing database connection to $DATABASE_NAME@$DATABASE_HOST:$DATABASE_PORT"

    if PGPASSWORD="${DB_PASSWORD:-}" psql \
        --host="$DATABASE_HOST" \
        --port="$DATABASE_PORT" \
        --username="$DATABASE_USER" \
        --dbname="$DATABASE_NAME" \
        --no-password \
        -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "Database connection successful"
    else
        log_error "Cannot connect to database"
        exit 1
    fi
}

# Check if database exists
check_database_exists() {
    if PGPASSWORD="${DB_PASSWORD:-}" psql \
        --host="$DATABASE_HOST" \
        --port="$DATABASE_PORT" \
        --username="$DATABASE_USER" \
        --dbname="postgres" \
        --no-password \
        -tAc "SELECT 1 FROM pg_database WHERE datname='$DATABASE_NAME'" | grep -q 1; then
        return 0
    else
        return 1
    fi
}

# Backup existing database
backup_existing_database() {
    if check_database_exists; then
        local timestamp=$(date '+%Y%m%d_%H%M%S')
        local backup_file="$BACKUP_DIR/database/pre_restore_backup_${timestamp}.sql.gz"

        log_info "Backing up existing database to: $backup_file"

        PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
            --host="$DATABASE_HOST" \
            --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" \
            --dbname="$DATABASE_NAME" \
            --no-password \
            --format=custom \
            --compress=9 \
            --file="$backup_file"

        if [[ $? -eq 0 ]]; then
            log_success "Existing database backed up successfully"
            log_info "Backup location: $backup_file"
        else
            log_error "Failed to backup existing database"
            exit 1
        fi
    else
        log_info "Database does not exist, no backup needed"
    fi
}

# Create database if it doesn't exist
create_database() {
    if ! check_database_exists; then
        log_info "Creating database: $DATABASE_NAME"

        PGPASSWORD="${DB_PASSWORD:-}" createdb \
            --host="$DATABASE_HOST" \
            --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" \
            "$DATABASE_NAME"

        if [[ $? -eq 0 ]]; then
            log_success "Database created successfully"
        else
            log_error "Failed to create database"
            exit 1
        fi
    else
        log_info "Database already exists"
    fi
}

# Drop existing database
drop_database() {
    if check_database_exists; then
        log_warning "Dropping existing database: $DATABASE_NAME"

        # Disconnect all users
        PGPASSWORD="${DB_PASSWORD:-}" psql \
            --host="$DATABASE_HOST" \
            --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" \
            --dbname="postgres" \
            --no-password \
            -c "
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '$DATABASE_NAME';
            " >/dev/null 2>&1

        # Drop database
        PGPASSWORD="${DB_PASSWORD:-}" dropdb \
            --host="$DATABASE_HOST" \
            --port="$DATABASE_PORT" \
            --username="$DATABASE_USER" \
            "$DATABASE_NAME"

        if [[ $? -eq 0 ]]; then
            log_success "Existing database dropped"
        else
            log_error "Failed to drop existing database"
            exit 1
        fi
    fi
}

# Restore database
restore_database() {
    log_info "Restoring database from: $BACKUP_FILE"

    local start_time=$(date +%s)

    # Create database
    create_database

    # Restore based on format
    case "$BACKUP_FORMAT" in
        "plain")
            log_info "Restoring from plain SQL dump"
            PGPASSWORD="${DB_PASSWORD:-}" psql \
                --host="$DATABASE_HOST" \
                --port="$DATABASE_PORT" \
                --username="$DATABASE_USER" \
                --dbname="$DATABASE_NAME" \
                --no-password \
                < "$BACKUP_FILE"
            ;;
        "gzip")
            log_info "Restoring from gzip compressed dump"
            gunzip -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD:-}" psql \
                --host="$DATABASE_HOST" \
                --port="$DATABASE_PORT" \
                --username="$DATABASE_USER" \
                --dbname="$DATABASE_NAME" \
                --no-password
            ;;
        "bzip2")
            log_info "Restoring from bzip2 compressed dump"
            bunzip2 -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD:-}" psql \
                --host="$DATABASE_HOST" \
                --port="$DATABASE_PORT" \
                --username="$DATABASE_USER" \
                --dbname="$DATABASE_NAME" \
                --no-password
            ;;
        "xz")
            log_info "Restoring from xz compressed dump"
            unxz -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD:-}" psql \
                --host="$DATABASE_HOST" \
                --port="$DATABASE_PORT" \
                --username="$DATABASE_USER" \
                --dbname="$DATABASE_NAME" \
                --no-password
            ;;
    esac

    local restore_result=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ $restore_result -eq 0 ]]; then
        log_success "Database restored successfully in ${duration}s"
    else
        log_error "Database restore failed"
        exit 1
    fi
}

# Verify restored database
verify_restored_database() {
    log_info "Verifying restored database..."

    # Check if tables exist
    local table_count=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        --host="$DATABASE_HOST" \
        --port="$DATABASE_PORT" \
        --username="$DATABASE_USER" \
        --dbname="$DATABASE_NAME" \
        --no-password \
        -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")

    if [[ -n "$table_count" && "$table_count" -gt 0 ]]; then
        log_success "Database restored with $table_count tables"
    else
        log_error "No tables found in restored database"
        return 1
    fi

    # Check if data exists
    local row_count=$(PGPASSWORD="${DB_PASSWORD:-}" psql \
        --host="$DATABASE_HOST" \
        --port="$DATABASE_PORT" \
        --username="$DATABASE_USER" \
        --dbname="$DATABASE_NAME" \
        --no-password \
        -tAc "SELECT sum(n_tup_ins) FROM pg_stat_user_tables WHERE schemaname = 'public'" 2>/dev/null || echo "0")

    if [[ -n "$row_count" && "$row_count" -gt 0 ]]; then
        log_success "Database contains data: $row_count rows"
    else
        log_warning "Database appears to be empty"
    fi

    # Run database-specific validation if it exists
    if PGPASSWORD="${DB_PASSWORD:-}" psql \
        --host="$DATABASE_HOST" \
        --port="$DATABASE_PORT" \
        --username="$DATABASE_USER" \
        --dbname="$DATABASE_NAME" \
        --no-password \
        -c "SELECT 1 FROM matches LIMIT 1;" >/dev/null 2>&1; then
        log_success "Core tables accessible"
    else
        log_warning "Core tables may not be accessible"
    fi
}

# Show restore summary
show_restore_summary() {
    log_info "Restore Summary:"
    log_info "  Source: $BACKUP_FILE"
    log_info "  Target: $DATABASE_NAME@$DATABASE_HOST:$DATABASE_PORT"
    log_info "  Format: $BACKUP_FORMAT"
    log_info "  User: $DATABASE_USER"
    log_info "  Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN: No changes were made"
    else
        log_success "Database restore completed successfully"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "🗄️ Football Prediction Database Restore"
    echo "=========================================="
    echo "Backup File: $BACKUP_FILE"
    echo "Target: $DATABASE_NAME@$DATABASE_HOST:$DATABASE_PORT"
    echo ""

    # Load environment
    load_env

    # Validate backup file
    validate_backup_file

    # Check database connection
    check_database_connection

    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN MODE - No changes will be made"

        log_info "Would perform the following steps:"
        if check_database_exists; then
            if [[ "$BACKUP_EXISTING" == "true" ]]; then
                echo "  1. Backup existing database"
            fi
            if [[ "$FORCE_RESTORE" == "true" ]]; then
                echo "  2. Drop existing database"
            else
                echo "  2. WARNING: Database exists and --force not specified"
            fi
        else
            echo "  1. Create new database"
        fi
        echo "  3. Restore from backup file"
        echo "  4. Verify restored database"

        show_restore_summary
        exit 0
    fi

    # Handle existing database
    if check_database_exists; then
        if [[ "$FORCE_RESTORE" == "true" ]]; then
            if [[ "$BACKUP_EXISTING" == "true" ]]; then
                backup_existing_database
            fi
            drop_database
        else
            log_error "Database already exists. Use --force to overwrite or --backup-existing to backup first."
            exit 1
        fi
    fi

    # Restore database
    restore_database

    # Verify restore
    verify_restored_database

    # Show summary
    show_restore_summary
}

# Run main function
main