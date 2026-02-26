-- ============================================================================
-- V57.4 DBA Manual Fix Script
-- ============================================================================
--
-- PROBLEM:
--   The metrics_multi_source_data table is missing production-grade audit fields
--   required by OddsProductionExtractor.save_multi_source_data()
--
-- ROOT CAUSE:
--   Multiple ALTER TABLE statements are blocked by AccessExclusiveLock.
--   17+ pending transactions are waiting for table modification.
--
-- SOLUTION:
--   DBA must execute this script during maintenance window when traffic is low.
--
-- ============================================================================

-- Step 1: Check for blocking locks (run as DBA)
SELECT
    l.pid,
    a.usename,
    a.query_start,
    LEFT(a.query, 50) as query_preview
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.relation = 'metrics_multi_source_data'::regclass
AND l.granted = false
ORDER BY a.query_start;

-- Step 2: Terminate blocking processes (if safe to do so)
-- Uncomment and run with actual PIDs from Step 1:
-- SELECT pg_terminate_backend(<pid>);
-- SELECT pg_terminate_backend(<pid>);
-- ...

-- Step 3: Verify no blocking locks remain
SELECT COUNT(*) as blocking_locks
FROM pg_locks l
WHERE l.relation = 'metrics_multi_source_data'::regclass
AND l.granted = false;

-- Step 4: Add missing columns (V57.4 production audit fields)
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;

ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS validation_error TEXT;

ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS fully_captured BOOLEAN DEFAULT FALSE;

ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS data_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 5: Verify columns were added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'metrics_multi_source_data'
AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
ORDER BY column_name;

-- Expected output:
-- column_name      | data_type              | column_default
-- -----------------+------------------------+-------------------
-- data_timestamp   | timestamp without time zone | CURRENT_TIMESTAMP
-- fully_captured   | boolean                 | false
-- is_valid         | boolean                 | true
-- validation_error | text                    | null

-- Step 6: Create optional indexes for audit fields
CREATE INDEX IF NOT EXISTS idx_multisource_is_valid
ON metrics_multi_source_data(is_valid) WHERE is_valid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_multisource_fully_captured
ON metrics_multi_source_data(fully_captured) WHERE fully_captured IS NOT NULL;

-- ============================================================================
-- Post-Migration Verification
-- ============================================================================

-- Run E2E test to verify fix:
--   python tests/unit/test_v57_4_persistence.py
--
-- Expected output:
--   === V57.4 E2E Persistence Test ===
--   1. Testing database connection... ✅ Connection OK
--   2. Testing MultiSourceEntityData model... ✅ Model OK
--   3. Testing persistence... ✅ Persistence OK
--   === ALL TESTS PASSED ===

-- ============================================================================
-- Rollback (if needed)
-- ============================================================================
-- ALTER TABLE metrics_multi_source_data DROP COLUMN IF EXISTS is_valid;
-- ALTER TABLE metrics_multi_source_data DROP COLUMN IF EXISTS validation_error;
-- ALTER TABLE metrics_multi_source_data DROP COLUMN IF EXISTS fully_captured;
-- ALTER TABLE metrics_multi_source_data DROP COLUMN IF EXISTS data_timestamp;
