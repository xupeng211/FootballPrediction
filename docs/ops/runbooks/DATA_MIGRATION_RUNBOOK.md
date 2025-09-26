# Data Migration Runbook

## 1. Overview

This runbook provides procedures for migrating data in the Football Prediction System, including schema changes, data model updates, and system upgrades.

## 2. Pre-Migration Preparation

### 2.1 Migration Planning

1. **Define Migration Scope**
   - Identify tables and data to be migrated
   - Determine migration type (schema-only, data-only, or both)
   - Estimate migration time and resources required

2. **Create Migration Plan**
   ```markdown
   # Migration Plan Template

   ## Migration Details
   - Version: [from_version] -> [to_version]
   - Date: [migration_date]
   - Downtime Window: [start_time] - [end_time]
   - Migration Type: [schema/data/both]

   ## Affected Components
   - [component_1]
   - [component_2]

   ## Rollback Plan
   - [rollback_steps]

   ## Validation Criteria
   - [validation_steps]
   ```

3. **Backup Current System**
   ```bash
   # Perform full backup before migration
   ./scripts/backup.sh --type full --database football_prediction

   # Verify backup integrity
   ./scripts/restore.sh --validate --backup-file /backup/football_db/full/latest_backup.sql.gz
   ```

### 2.2 Environment Preparation

1. **Prepare Migration Environment**
   ```bash
   # Create migration branch
   git checkout -b migration-v[version]

   # Update dependencies
   pip install -r requirements.txt

   # Run tests
   pytest tests/migration/
   ```

2. **Test Migration on Staging**
   ```bash
   # Deploy to staging environment
   docker-compose -f docker-compose.staging.yml up -d

   # Run migration
   alembic upgrade head

   # Validate migration
   python scripts/validate_migration.py
   ```

## 3. Migration Procedures

### 3.1 Database Schema Migration

#### 3.1.1 Alembic Migration

1. **Generate Migration Script**
   ```bash
   # Generate new migration script
   alembic revision --autogenerate -m "Add new prediction metrics columns"

   # Review generated migration script
   cat alembic/versions/[timestamp]_add_new_prediction_metrics_columns.py
   ```

2. **Customize Migration Script**
   ```python
   # alembic/versions/[timestamp]_add_new_prediction_metrics_columns.py
   from alembic import op
   import sqlalchemy as sa

   def upgrade():
       # Add new columns
       op.add_column('predictions', sa.Column('model_accuracy', sa.Float(), nullable=True))
       op.add_column('predictions', sa.Column('feature_importance', sa.JSON(), nullable=True))

       # Add indexes
       op.create_index('idx_predictions_model_accuracy', 'predictions', ['model_accuracy'])

       # Update existing records
       op.execute("""
           UPDATE predictions
           SET model_accuracy = 0.85
           WHERE model_version = '1.0'
       """)

   def downgrade():
       # Remove columns
       op.drop_column('predictions', 'feature_importance')
       op.drop_column('predictions', 'model_accuracy')

       # Remove indexes
       op.drop_index('idx_predictions_model_accuracy', table_name='predictions')
   ```

3. **Test Migration Script**
   ```bash
   # Test upgrade
   alembic upgrade +1

   # Test downgrade
   alembic downgrade -1

   # Test full cycle
   alembic upgrade head
   alembic downgrade base
   alembic upgrade head
   ```

#### 3.1.2 Manual Schema Changes

1. **Apply Schema Changes**
   ```bash
   # Apply changes directly (for complex migrations)
   psql -h localhost -p 5432 -U football_user -d football_prediction -f migrations/schema_changes.sql
   ```

2. **Verify Schema Changes**
   ```sql
   -- migrations/verify_schema.sql
   -- Check table structure
   \d predictions

   -- Check constraints
   SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'predictions';

   -- Check indexes
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'predictions';
   ```

### 3.2 Data Migration

#### 3.2.1 Batch Data Migration

1. **Create Data Migration Script**
   ```python
   # scripts/migrate_prediction_data.py
   import asyncio
   import logging
   from sqlalchemy import select, update
   from src.database.connection import DatabaseManager
   from src.database.models.predictions import Predictions

   logger = logging.getLogger(__name__)

   async def migrate_prediction_data(batch_size=1000):
       """Migrate prediction data in batches"""
       db_manager = DatabaseManager()

       async with db_manager.get_async_session() as session:
           # Get total count
           result = await session.execute(select(sa.func.count()).select_from(Predictions))
           total_count = result.scalar()

           logger.info(f"Starting migration of {total_count} predictions")

           # Process in batches
           offset = 0
           while offset < total_count:
               # Get batch
               result = await session.execute(
                   select(Predictions).offset(offset).limit(batch_size)
               )
               predictions = result.scalars().all()

               # Process batch
               for prediction in predictions:
                   # Calculate new metrics
                   accuracy = calculate_accuracy(prediction)
                   importance = calculate_feature_importance(prediction)

                   # Update record
                   await session.execute(
                       update(Predictions)
                       .where(Predictions.id == prediction.id)
                       .values(
                           model_accuracy=accuracy,
                           feature_importance=importance
                       )
                   )

               # Commit batch
               await session.commit()
               logger.info(f"Processed {min(offset + batch_size, total_count)}/{total_count} predictions")

               offset += batch_size

   def calculate_accuracy(prediction):
       """Calculate model accuracy for prediction"""
       # Implementation here
       return 0.85

   def calculate_feature_importance(prediction):
       """Calculate feature importance for prediction"""
       # Implementation here
       return {"feature1": 0.3, "feature2": 0.7}

   if __name__ == "__main__":
       asyncio.run(migrate_prediction_data())
   ```

2. **Run Data Migration**
   ```bash
   # Run migration script
   python scripts/migrate_prediction_data.py --batch-size 500

   # Monitor progress
   tail -f logs/migration.log
   ```

#### 3.2.2 Incremental Data Migration

1. **Set Up Incremental Migration**
   ```python
   # scripts/incremental_migration.py
   import asyncio
   import logging
   from datetime import datetime, timedelta
   from sqlalchemy import select, update
   from src.database.connection import DatabaseManager
   from src.database.models.predictions import Predictions

   logger = logging.getLogger(__name__)

   async def incremental_migration(hours_back=24):
       """Perform incremental migration for recent data"""
       db_manager = DatabaseManager()

       # Calculate time window
       since_time = datetime.now() - timedelta(hours=hours_back)

       async with db_manager.get_async_session() as session:
           # Get recent predictions
           result = await session.execute(
               select(Predictions).where(Predictions.created_at >= since_time)
           )
           predictions = result.scalars().all()

           logger.info(f"Migrating {len(predictions)} recent predictions")

           # Process predictions
           for prediction in predictions:
               # Calculate new metrics
               accuracy = calculate_accuracy(prediction)
               importance = calculate_feature_importance(prediction)

               # Update record
               await session.execute(
                   update(Predictions)
                   .where(Predictions.id == prediction.id)
                   .values(
                       model_accuracy=accuracy,
                       feature_importance=importance
                   )
               )

           # Commit changes
           await session.commit()
           logger.info("Incremental migration completed")

   if __name__ == "__main__":
       asyncio.run(incremental_migration())
   ```

### 3.3 Application Migration

#### 3.3.1 Configuration Migration

1. **Update Configuration Files**
   ```bash
   # Update environment variables
   cp .env.production .env.production.backup
   nano .env.production

   # Update application configuration
   nano config/app_config.json
   ```

2. **Deploy New Configuration**
   ```bash
   # Deploy to staging
   docker-compose -f docker-compose.staging.yml up -d

   # Test configuration
   curl -f http://staging.footballprediction.com/health

   # Deploy to production
   docker-compose up -d
   ```

#### 3.3.2 Code Migration

1. **Deploy New Code**
   ```bash
   # Pull latest code
   git pull origin main

   # Build new images
   docker-compose build

   # Deploy with zero downtime (blue-green deployment)
   docker-compose -f docker-compose.blue.yml up -d
   # Test blue environment
   # Switch traffic to blue
   # Shutdown green environment

   # Or rolling update
   docker-compose up -d --no-deps --scale api=2 api
   docker-compose up -d --no-deps api
   docker-compose up -d --no-deps --scale api=1 api
   ```

## 4. Post-Migration Validation

### 4.1 Data Validation

1. **Verify Data Integrity**
   ```python
   # scripts/validate_migration.py
   import asyncio
   from sqlalchemy import select, func
   from src.database.connection import DatabaseManager
   from src.database.models.predictions import Predictions

   async def validate_migration():
       """Validate migration results"""
       db_manager = DatabaseManager()

       async with db_manager.get_async_session() as session:
           # Check record counts
           result = await session.execute(select(func.count()).select_from(Predictions))
           total_count = result.scalar()
           print(f"Total predictions: {total_count}")

           # Check migrated fields
           result = await session.execute(
               select(func.count())
               .select_from(Predictions)
               .where(Predictions.model_accuracy.isnot(None))
           )
           migrated_count = result.scalar()
           print(f"Migrated predictions: {migrated_count}")

           # Calculate migration percentage
           migration_percentage = (migrated_count / total_count) * 100
           print(f"Migration completion: {migration_percentage:.2f}%")

           # Check for data consistency
           result = await session.execute(
               select(Predictions)
               .where(Predictions.model_accuracy < 0)
               .limit(5)
           )
           invalid_records = result.scalars().all()
           if invalid_records:
               print(f"Found {len(invalid_records)} invalid records")
               return False

           print("Migration validation passed")
           return True

   if __name__ == "__main__":
       asyncio.run(validate_migration())
   ```

2. **Run Validation Script**
   ```bash
   # Run validation
   python scripts/validate_migration.py

   # Check detailed validation report
   cat reports/migration_validation_$(date +%Y%m%d).txt
   ```

### 4.2 Functional Validation

1. **Test Core Functionality**
   ```bash
   # Test API endpoints
   pytest tests/api/test_predictions.py

   # Test prediction service
   pytest tests/models/test_prediction_service.py

   # Test data pipeline
   pytest tests/integration/test_data_pipeline.py
   ```

2. **Performance Testing**
   ```bash
   # Run performance tests
   pytest tests/performance/test_prediction_performance.py

   # Monitor system metrics
   python scripts/monitor_system_metrics.py --duration 300
   ```

## 5. Rollback Procedures

### 5.1 Database Rollback

1. **Rollback Schema Changes**
   ```bash
   # Rollback to previous version
   alembic downgrade -1

   # Or rollback to specific revision
   alembic downgrade [revision_id]
   ```

2. **Restore from Backup**
   ```bash
   # Stop application
   docker-compose down

   # Restore database from backup
   ./scripts/restore.sh --backup-file /backup/football_db/full/backup_before_migration.sql.gz

   # Start application
   docker-compose up -d
   ```

### 5.2 Application Rollback

1. **Rollback to Previous Version**
   ```bash
   # Rollback code
   git checkout [previous_commit]

   # Rebuild and deploy
   docker-compose build
   docker-compose up -d
   ```

2. **Restore Configuration**
   ```bash
   # Restore previous configuration
   cp .env.production.backup .env.production

   # Restart services
   docker-compose restart
   ```

## 6. Monitoring and Monitoring

### 6.1 Migration Monitoring

1. **Real-time Monitoring**
   ```python
   # scripts/monitor_migration.py
   import time
   import logging
   from datetime import datetime
   from src.monitoring.metrics_collector import MigrationMetricsCollector

   logger = logging.getLogger(__name__)

   def monitor_migration():
       """Monitor migration progress in real-time"""
       collector = MigrationMetricsCollector()

       while True:
           try:
               # Collect migration metrics
               metrics = collector.collect_migration_metrics()

               # Log metrics
               logger.info(f"Migration Progress: {metrics['progress']:.2f}%")
               logger.info(f"Records Processed: {metrics['processed']}/{metrics['total']}")
               logger.info(f"Errors: {metrics['errors']}")

               # Check for issues
               if metrics['errors'] > 10:
                   logger.error("Too many errors detected, stopping migration")
                   break

               # Sleep before next check
               time.sleep(30)

           except KeyboardInterrupt:
               logger.info("Migration monitoring stopped by user")
               break
           except Exception as e:
               logger.error(f"Error monitoring migration: {e}")

   if __name__ == "__main__":
       monitor_migration()
   ```

2. **Dashboard Monitoring**
   ```bash
   # Open Grafana dashboard
   xdg-open http://localhost:3000/d/migration-dashboard/migration-monitoring

   # Check alerts
   curl -s http://localhost:9093/api/v2/alerts | jq '.[] | select(.labels.alertname=="migration_failure")'
   ```

## 7. Documentation and Communication

### 7.1 Migration Documentation

1. **Update Documentation**
   ```bash
   # Update API documentation
   make docs

   # Update data model documentation
   python scripts/generate_data_model_docs.py

   # Update migration history
   echo "$(date): Migration v[version] completed successfully" >> docs/MIGRATION_HISTORY.md
   ```

2. **Create Migration Report**
   ```markdown
   # Migration Report - v[version]

   ## Summary
   - Migration completed successfully on [date]
   - [X] records migrated
   - [Y] errors encountered and resolved
   - Downtime: [Z] minutes

   ## Changes
   - Added model_accuracy column to predictions table
   - Updated prediction service to calculate accuracy
   - Modified API to return accuracy metrics

   ## Issues Encountered
   - Issue 1: [description and resolution]
   - Issue 2: [description and resolution]

   ## Next Steps
   - Monitor system performance
   - Validate data integrity
   - Update runbooks and documentation
   ```

### 7.2 Stakeholder Communication

1. **Notify Stakeholders**
   ```bash
   # Send completion notification
   python scripts/notify_stakeholders.py --migration-complete --version [version]

   # Update status page
   python scripts/update_status_page.py --status operational
   ```

2. **Schedule Post-Mortem**
   ```bash
   # Create calendar event
   echo "Schedule post-migration review meeting" | mail -s "Migration Review Meeting" team@footballprediction.com
   ```

## 8. Contact Information

### 8.1 Migration Team

- **Migration Lead**: [Name] - [Phone] - [Email]
- **Database Administrator**: [Name] - [Phone] - [Email]
- **Application Developer**: [Name] - [Phone] - [Email]
- **QA Engineer**: [Name] - [Phone] - [Email]

### 8.2 Emergency Contacts

- **24/7 Support**: [Phone]
- **Database Emergency**: [Phone]
- **Infrastructure Emergency**: [Phone]
