#!/bin/bash

# =================================================================
# Disaster Recovery Script - Football Prediction System V1.1
# 一键恢复脚本 - 足球预测系统 V1.1
# =================================================================
# Usage: ./scripts/restart_pipeline.sh [--restore-from-backup]
# Options:
#   --restore-from-backup  Restore from golden snapshot (v1.1_stable_snapshot_26k.sql)
# =================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_FILE="data/backup/v1.1_stable_snapshot_26k.sql"
HEALTH_CHECK_URL="http://localhost:8000/health"
LOG_FILE="logs/recovery_$(date +%Y%m%d_%H%M%S).log"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Create log directory
mkdir -p logs
mkdir -p data/backup

# Header
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}    Football Prediction System V1.1 - Disaster Recovery${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
log_info "Starting recovery process at $(date)"
log_info "Log file: $LOG_FILE"

# Check if backup file exists when restore is requested
RESTORE_BACKUP=false
if [[ "$1" == "--restore-from-backup" ]]; then
    RESTORE_BACKUP=true
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "Backup file not found: $BACKUP_FILE"
        log_error "Please ensure the golden snapshot exists before attempting restore"
        exit 1
    fi
    log_info "Backup file found: $(du -h "$BACKUP_FILE" | cut -f1)"
fi

# Step 1: Stop existing containers
log_info "Step 1: Stopping existing containers..."
if docker-compose ps | grep -q "Up"; then
    log_info "Stopping running containers..."
    docker-compose down
    sleep 5
else
    log_info "No running containers found"
fi

# Step 2: Start Docker containers
log_info "Step 2: Starting Docker containers..."
docker-compose up -d

# Step 3: Wait for database to be ready
log_info "Step 3: Waiting for database to be ready..."
DB_READY=false
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        DB_READY=true
        break
    fi
    echo -n "."
    sleep 2
done

if [ "$DB_READY" = false ]; then
    log_error "Database failed to start within 60 seconds"
    exit 1
fi

echo ""
log_success "Database is ready!"

# Step 4: Restore from backup if requested
if [ "$RESTORE_BACKUP" = true ]; then
    log_info "Step 4: Restoring database from golden snapshot..."

    # Wait a bit more for database to fully initialize
    sleep 10

    # Restore database
    if docker-compose exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS football_prediction;" >/dev/null 2>&1; then
        log_info "Dropped existing database"
    fi

    if docker-compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE football_prediction;" >/dev/null 2>&1; then
        log_info "Created fresh database"
    fi

    if docker-compose exec -T db psql -U postgres -d football_prediction < "$BACKUP_FILE" >/dev/null 2>&1; then
        log_success "Database restored successfully from golden snapshot"

        # Get record count
        RECORD_COUNT=$(docker-compose exec -T db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;" 2>/dev/null | tr -d '[:space:]' || echo "unknown")
        log_info "Restored records: $RECORD_COUNT"
    else
        log_error "Database restore failed"
        exit 1
    fi
else
    log_info "Step 4: Skipping database restore (using existing data)"

    # Get current record count
    RECORD_COUNT=$(docker-compose exec -T db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;" 2>/dev/null | tr -d '[:space:]' || echo "unknown")
    log_info "Current records: $RECORD_COUNT"
fi

# Step 5: Run database migrations
log_info "Step 5: Running database migrations..."
docker-compose exec -T app bash -c "cd /app && python -m alembic upgrade head" >/dev/null 2>&1 || {
    log_warning "Database migrations failed or not needed"
}

# Step 6: Wait for application to be healthy
log_info "Step 6: Waiting for application to be healthy..."
APP_READY=false
for i in {1..60}; do
    if curl -s "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
        APP_READY=true
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
if [ "$APP_READY" = false ]; then
    log_error "Application failed to become healthy within 120 seconds"
    log_error "Please check application logs: docker-compose logs app"
    exit 1
fi

log_success "Application is healthy!"

# Step 7: Start background services if needed
log_info "Step 7: Starting background services..."

# Check if Celery worker is running
if ! docker-compose exec -T app bash -c "celery -A src.tasks.celery_app inspect ping" >/dev/null 2>&1; then
    log_info "Starting Celery worker..."
    docker-compose exec -d app bash -c "cd /app && celery -A src.tasks.celery_app worker --loglevel=info" || {
        log_warning "Failed to start Celery worker"
    }
else
    log_success "Celery worker is already running"
fi

# Step 8: Trigger L1 data collection if needed (optional)
log_info "Step 8: Checking L1 data collection status..."
L1_STATUS=$(curl -s "$HEALTH_CHECK_URL" | jq -r '.data_collection.l1_status' 2>/dev/null || echo "unknown")

if [[ "$L1_STATUS" == "inactive" || "$L1_STATUS" == "unknown" ]]; then
    log_warning "L1 data collection is inactive. You may want to trigger it manually:"
    log_warning "  curl -X POST http://localhost:8000/api/v1/data/collect/l1"
else
    log_success "L1 data collection status: $L1_STATUS"
fi

# Step 9: Final status report
log_info "Step 9: Generating final status report..."
echo ""
echo -e "${GREEN}==================== RECOVERY COMPLETE ====================${NC}"
echo -e "${GREEN}System Status:${NC}"
echo -e "  📊 Database: ${GREEN}Online${NC}"
echo -e "  🌐 API: ${GREEN}Healthy${NC} ($HEALTH_CHECK_URL)"
echo -e "  📈 Records: ${GREEN}$RECORD_COUNT${NC}"

# Check service status
echo ""
echo -e "${BLUE}Service Status:${NC}"
docker-compose ps

# Show API endpoints
echo ""
echo -e "${BLUE}Available Endpoints:${NC}"
echo -e "  🌐 Frontend: ${YELLOW}http://localhost:3000${NC}"
echo -e "  🔧 Backend API: ${YELLOW}http://localhost:8000${NC}"
echo -e "  📚 API Documentation: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "  📊 Health Check: ${YELLOW}http://localhost:8000/health${NC}"
echo -e "  📈 Metrics: ${YELLOW}http://localhost:8000/api/v1/metrics${NC}"

# Next steps
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
if [ "$RESTORE_BACKUP" = true ]; then
    echo -e "  ✅ Database restored from golden snapshot"
    echo -e "  🔄 Consider running L1 data collection for latest matches"
else
    echo -e "  📊 Using existing database"
fi
echo -e "  📈 Monitor system health: ${BLUE}curl http://localhost:8000/health${NC}"
echo -e "  📋 View logs: ${BLUE}docker-compose logs -f${NC}"
echo -e "  🎯 Start L1 collection: ${BLUE}curl -X POST http://localhost:8000/api/v1/data/collect/l1${NC}"

echo ""
log_success "Recovery process completed successfully at $(date)"
echo -e "${GREEN}🎉 Football Prediction System V1.1 is now operational!${NC}"
echo ""

# Save recovery info
{
    echo "Recovery completed at: $(date)"
    echo "Backup restored: $RESTORE_BACKUP"
    echo "Record count: $RECORD_COUNT"
    echo "Git version: $(git describe --tags 2>/dev/null || echo 'unknown')"
} >> "logs/recovery_history.txt"

echo -e "${BLUE}Recovery log saved to: $LOG_FILE${NC}"
echo -e "${BLUE}Recovery history: logs/recovery_history.txt${NC}"