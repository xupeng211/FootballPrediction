# Disaster Recovery Runbook

## 1. Overview

This runbook provides step-by-step procedures for disaster recovery of the Football Prediction System. It covers recovery from various failure scenarios including database corruption, system failures, and data loss.

## 2. Recovery Scenarios

### 2.1 Database Recovery

#### 2.1.1 Full Database Recovery from Backup

**Prerequisites:**
- Access to backup files
- Database administrator privileges
- Backup restoration scripts

**Procedure:**

1. **Identify Latest Backup**
   ```bash
   # List available backups
   ls -la /backup/football_db/full/

   # Identify latest backup file
   LATEST_BACKUP=$(ls -t /backup/football_db/full/full_backup_*.sql.gz | head -1)
   echo "Latest backup: $LATEST_BACKUP"
   ```

2. **Stop Application Services**
   ```bash
   # Stop all application services
   docker-compose stop

   # Stop database service
   docker-compose stop db
   ```

3. **Restore Database**
   ```bash
   # Run database restoration script
   ./scripts/restore.sh --backup-file $LATEST_BACKUP --database football_prediction

   # Or manually restore (if script fails)
   gunzip -c $LATEST_BACKUP | psql -h localhost -p 5432 -U football_user -d football_prediction
   ```

4. **Verify Restoration**
   ```bash
   # Connect to database and verify data
   psql -h localhost -p 5432 -U football_user -d football_prediction -c "SELECT COUNT(*) FROM matches;"
   ```

5. **Restart Services**
   ```bash
   # Start database service
   docker-compose up -d db

   # Start all services
   docker-compose up -d
   ```

#### 2.1.2 Point-in-Time Recovery (PITR)

**Prerequisites:**
- WAL archives available
- Base backup
- Target recovery time

**Procedure:**

1. **Stop Database Service**
   ```bash
   docker-compose stop db
   ```

2. **Prepare Recovery Configuration**
   ```bash
   # Create recovery.conf file
   cat > /backup/football_db/recovery.conf << EOF
   restore_command = 'cp /backup/football_db/wal/%f %p'
   recovery_target_time = '2025-09-15 10:00:00'
   EOF
   ```

3. **Restore Base Backup**
   ```bash
   # Restore latest base backup
   ./scripts/restore.sh --type base --backup-dir /backup/football_db/base/latest
   ```

4. **Start Database in Recovery Mode**
   ```bash
   # Start database (it will automatically enter recovery mode)
   docker-compose up -d db
   ```

5. **Monitor Recovery Process**
   ```bash
   # Monitor recovery progress
   docker-compose logs -f db

   # Check recovery status
   psql -h localhost -p 5432 -U football_user -d football_prediction -c "SELECT pg_is_in_recovery();"
   ```

6. **Complete Recovery**
   ```bash
   # Promote database to primary
   psql -h localhost -p 5432 -U football_user -d football_prediction -c "SELECT pg_promote();"
   ```

### 2.2 Application Service Recovery

#### 2.2.1 Complete Application Recovery

**Prerequisites:**
- Access to application servers
- Docker/Docker Compose installed
- Application configuration files

**Procedure:**

1. **Check System Status**
   ```bash
   # Check Docker status
   systemctl status docker

   # Check disk space
   df -h

   # Check memory usage
   free -h
   ```

2. **Clean Up Failed Containers**
   ```bash
   # Stop all containers
   docker-compose down

   # Remove orphan containers
   docker system prune -f

   # Remove unused volumes
   docker volume prune -f
   ```

3. **Rebuild Application**
   ```bash
   # Pull latest images
   docker-compose pull

   # Build services
   docker-compose build --no-cache

   # Start services
   docker-compose up -d
   ```

4. **Verify Application Health**
   ```bash
   # Check service status
   docker-compose ps

   # Check application health endpoint
   curl -f http://localhost:8000/health || echo "Health check failed"

   # Check logs
   docker-compose logs --tail=100
   ```

### 2.3 Data Pipeline Recovery

#### 2.3.1 Restart Failed Data Pipeline

**Prerequisites:**
- Access to task queue (Redis/Celery)
- Pipeline monitoring tools

**Procedure:**

1. **Identify Failed Tasks**
   ```bash
   # Check Celery task status
   celery -A src.tasks.celery_app inspect active
   celery -A src.tasks.celery_app inspect reserved
   celery -A src.tasks.celery_app inspect scheduled

   # Check failed tasks in Redis
   redis-cli -h redis -p 6379 KEYS "celery-task-meta-*" | head -10
   ```

2. **Restart Failed Tasks**
   ```bash
   # Restart specific task
   python -c "
   from src.tasks.celery_app import app
   app.control.revoke('task-id', terminate=True)
   "

   # Or restart all failed tasks
   python scripts/restart_failed_tasks.py
   ```

3. **Clear Task Queue if Needed**
   ```bash
   # Clear specific queue
   celery -A src.tasks.celery_app purge -Q data_collection

   # Clear all queues
   celery -A src.tasks.celery_app purge
   ```

4. **Restart Pipeline Services**
   ```bash
   # Restart task workers
   docker-compose restart celery-worker

   # Restart scheduler
   docker-compose restart celery-beat
   ```

## 3. Monitoring and Validation

### 3.1 Post-Recovery Validation

1. **Database Validation**
   ```bash
   # Check database connectivity
   python -c "
   from src.database.connection import DatabaseManager
   db = DatabaseManager()
   db.initialize()
   assert db.health_check(), 'Database health check failed'
   print('Database is healthy')
   "

   # Verify data integrity
   python scripts/verify_data_integrity.py
   ```

2. **Application Validation**
   ```bash
   # Test API endpoints
   curl -f http://localhost:8000/api/v1/health
   curl -f http://localhost:8000/api/v1/predictions/recent?limit=5

   # Test prediction functionality
   python scripts/test_prediction_functionality.py
   ```

3. **Pipeline Validation**
   ```bash
   # Check task processing
   python scripts/monitor_task_queue.py --check-active

   # Verify data flow
   python scripts/verify_data_pipeline.py
   ```

### 3.2 Performance Monitoring

1. **System Resources**
   ```bash
   # Monitor system resources
   top -b -n 1 | head -20
   iostat -x 1 5
   ```

2. **Database Performance**
   ```bash
   # Check database performance
   python scripts/monitor_database_performance.py
   ```

3. **Application Performance**
   ```bash
   # Monitor API response times
   python scripts/monitor_api_performance.py
   ```

## 4. Communication and Documentation

### 4.1 Incident Reporting

1. **Create Incident Report**
   ```bash
   # Generate incident report template
   cat > incident_reports/incident_$(date +%Y%m%d_%H%M%S).md << EOF
   # Incident Report

   ## Summary

   ## Timeline

   ## Impact

   ## Root Cause

   ## Resolution

   ## Preventive Measures

   ## Follow-up Actions
   EOF
   ```

2. **Notify Stakeholders**
   ```bash
   # Send notification to team
   python scripts/notify_stakeholders.py --incident --severity high

   # Update status page
   python scripts/update_status_page.py --status operational
   ```

## 5. Preventive Measures

### 5.1 Regular Backup Verification

```bash
# Weekly backup verification script
#!/bin/bash
set -e

echo "Starting backup verification..."

# Test backup restoration
LATEST_BACKUP=$(ls -t /backup/football_db/full/full_backup_*.sql.gz | head -1)
TEST_DB="football_prediction_test_$(date +%s)"

# Create test database
createdb $TEST_DB

# Restore backup to test database
gunzip -c $LATEST_BACKUP | psql -d $TEST_DB

# Verify data integrity
psql -d $TEST_DB -c "SELECT COUNT(*) FROM matches;" > /tmp/backup_verification.log

# Clean up
dropdb $TEST_DB

echo "Backup verification completed successfully"
```

### 5.2 Automated Health Checks

```python
# scripts/automated_health_check.py
import asyncio
import sys
from src.database.connection import DatabaseManager
from src.monitoring.quality_monitor import QualityMonitor

async def health_check():
    """Perform comprehensive health check"""
    try:
        # Database health check
        db_manager = DatabaseManager()
        if not db_manager.health_check():
            raise Exception("Database health check failed")

        # Data quality check
        quality_monitor = QualityMonitor()
        freshness_results = await quality_monitor.check_data_freshness()

        # Check if any critical tables are stale
        stale_tables = [table for table, result in freshness_results.items()
                       if not result.is_fresh and result.threshold_hours < 24]

        if stale_tables:
            raise Exception(f"Stale tables detected: {stale_tables}")

        print("All health checks passed")
        return True

    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)
```

## 6. Contact Information

### 6.1 Emergency Contacts

- **Primary On-Call**: [Name] - [Phone] - [Email]
- **Secondary On-Call**: [Name] - [Phone] - [Email]
- **Database Administrator**: [Name] - [Phone] - [Email]
- **System Administrator**: [Name] - [Phone] - [Email]

### 6.2 Service Dependencies

- **Database**: PostgreSQL
- **Cache**: Redis
- **Message Queue**: Celery with Redis
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack
