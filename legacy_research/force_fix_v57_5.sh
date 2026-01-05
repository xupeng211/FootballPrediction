#!/bin/bash
# V57.5 One-Click Force Fix - Docker Compose Edition

echo "=========================================="
echo "V57.5 FORCE FIX - One-Click Clearance"
echo "=========================================="

# DB connection details
DB_HOST="db"
DB_USER="football_user"
DB_NAME="football_prediction_dev"

# Get password from .env
DB_PASSWORD=$(grep ^DB_PASSWORD .env | cut -d= -f2)

echo ""
echo "[STEP 1] Killing zombie processes..."
docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" << EOSQL
SELECT pg_terminate_backend(pid) as killed
FROM pg_stat_activity
WHERE pid IN (53004, 53086, 53094, 53132, 53193, 53297, 53419, 53465)
AND pid <> pg_backend_pid();
EOSQL

echo ""
echo "[STEP 2] Adding missing columns..."
docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" << EOSQL
ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;
ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS validation_error TEXT;
ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS fully_captured BOOLEAN DEFAULT FALSE;
ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS data_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
EOSQL

echo ""
echo "[STEP 3] Verification..."
docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" << EOSQL
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'metrics_multi_source_data'
AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
ORDER BY column_name;
EOSQL

echo ""
echo "=========================================="
echo "Next: Run E2E test"
echo "  python tests/unit/test_v57_4_persistence.py"
echo "=========================================="
