-- ============================================================================
-- V70.300 - Emergency Recovery SQL Templates
-- ============================================================================
--
-- This file contains SQL templates for emergency recovery procedures.
-- USE WITH CAUTION - These scripts can modify large amounts of data.
--
-- @file v70_300_emergency_recovery.sql
-- @version V70.300
-- @since 2026-01-25
--
-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
--
-- 1. Review the SQL script before execution
-- 2. Test in non-production environment first
-- 3. Backup database before running:
--    ./scripts/ops/control.sh backup
-- 4. Execute with:
--    psql -h 172.25.16.1 -U football_user -d football_db -f v70_300_emergency_recovery.sql
--    OR
--    docker exec -i football_db psql -U football_user -d football_db < v70_300_emergency_recovery.sql
--
-- ============================================================================

-- ============================================================================
-- RECOVERY 1: Mass Reset FAILED Records to DISCOVERED
-- ============================================================================
-- Description: Reset all FAILED records to DISCOVERED state for retry
-- Use Case: System-wide failure recovery
-- Impact: HIGH - affects all failed records
-- ============================================================================

\echo 'RECOVERY 1: Resetting all FAILED records to DISCOVERED...'

BEGIN;

UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW()
WHERE status = 'FAILED';

-- Log the reset
INSERT INTO pipeline_audit_log (operation, affected_count, performed_at)
SELECT 'MASS_RESET_TO_DISCOVERED', COUNT(*), NOW()
FROM match_pipeline_state
WHERE status = 'DISCOVERED'
  AND updated_at > NOW() - INTERVAL '1 minute';

COMMIT;

-- Verify result
SELECT 'RECOVERY 1 Complete' as status, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;


-- ============================================================================
-- RECOVERY 2: Reset FAILED to Previous Valid State
-- ============================================================================
-- Description: Intelligently reset FAILED records to their previous valid state
-- Use Case: Selective recovery without losing progress
-- Impact: MEDIUM - only affects failed records
-- ============================================================================

\echo 'RECOVERY 2: Resetting FAILED records to previous valid state...'

BEGIN;

-- Step 2A: FAILED -> MAPPED (for odds harvest failures)
UPDATE match_pipeline_state mps
SET status = 'MAPPED', updated_at = NOW()
WHERE mps.status = 'FAILED'
  AND EXISTS (
      SELECT 1 FROM matches_mapping mm
      WHERE mm.fotmob_id = mps.match_id
        AND mm.oddsportal_url IS NOT NULL
  );

-- Step 2B: FAILED -> ENRICHED (for bridge mapping failures)
UPDATE match_pipeline_state mps
SET status = 'ENRICHED', updated_at = NOW()
WHERE mps.status = 'FAILED'
  AND EXISTS (
      SELECT 1 FROM matches m
      WHERE m.match_id = mps.match_id
        AND m.l2_raw_json IS NOT NULL
  );

-- Step 2C: Remaining FAILED -> DISCOVERED
UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW()
WHERE status = 'FAILED';

COMMIT;

-- Verify result
SELECT 'RECOVERY 2 Complete' as status, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;


-- ============================================================================
-- RECOVERY 3: Selective League Re-harvest
-- ============================================================================
-- Description: Reset specific league to ENRICHED (skip L2, redo bridge + harvest)
-- Use Case: League-wide data quality issues
-- Impact: MEDIUM - affects only specified league
-- Parameters: Replace 'Premier League' with target league
-- ============================================================================

\echo 'RECOVERY 3: Re-harvesting Premier League...'

BEGIN;

UPDATE match_pipeline_state mps
SET status = 'ENRICHED', updated_at = NOW()
FROM matches m
WHERE mps.match_id = m.match_id
  AND m.league_name = 'Premier League'
  AND mps.status IN ('MAPPED', 'HARVESTED', 'FAILED');

COMMIT;

-- Verify result
SELECT 'RECOVERY 3 Complete' as status,
       league_name,
       mps.status,
       COUNT(*) as count
FROM match_pipeline_state mps
JOIN matches m ON mps.match_id = m.match_id
WHERE m.league_name = 'Premier League'
GROUP BY league_name, mps.status
ORDER BY mps.status;


-- ============================================================================
-- RECOVERY 4: Clean Corrupted Temporal Records
-- ============================================================================
-- Description: Remove records with anomalous payout values
-- Use Case: Data quality gate alerts
-- Impact: LOW-MEDIUM - removes only corrupted records
-- ============================================================================

\echo 'RECOVERY 4: Cleaning corrupted temporal records...'

BEGIN;

-- Display count before cleanup
SELECT 'Before cleanup' as stage, COUNT(*) as count
FROM temporal_metric_records
WHERE payout < 0.70 OR payout > 1.10;

-- Delete corrupted records
DELETE FROM temporal_metric_records
WHERE payout < 0.70 OR payout > 1.10;

-- Reset affected matches to MAPPED
UPDATE match_pipeline_state
SET status = 'MAPPED', updated_at = NOW()
WHERE match_id IN (
    SELECT DISTINCT entity_id::varchar
    FROM temporal_metric_records
    WHERE payout < 0.70 OR payout > 1.10
);

COMMIT;

-- Verify result
SELECT 'RECOVERY 4 Complete' as stage, COUNT(*) as remaining_count
FROM temporal_metric_records
WHERE payout < 0.70 OR payout > 1.10;


-- ============================================================================
-- RECOVERY 5: Rebuild Entity Mapping for League
-- ============================================================================
-- Description: Rebuild entities_mapping table for specific league
-- Use Case: Entity mapping corruption or missing data
-- Impact: MEDIUM - affects only specified league
-- ============================================================================

\echo 'RECOVERY 5: Rebuilding entity mapping for Premier League...'

BEGIN;

-- Delete existing mappings for league (optional - comment out if not needed)
/*
DELETE FROM entities_mapping
WHERE source_system = 'oddsportal'
  AND entity_type = 'match'
  AND source_url LIKE '%premier-league%';
*/

-- Identify matches needing remapping
CREATE TEMP TABLE remap_candidates AS
SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
FROM matches m
LEFT JOIN entities_mapping em ON em.source_id::varchar = m.match_id
WHERE m.league_name = 'Premier League'
  AND em.entity_id IS NULL
LIMIT 100;

-- Show count
SELECT 'RECOVERY 5 Complete' as status, COUNT(*) as candidates_to_remap
FROM remap_candidates;

COMMIT;


-- ============================================================================
-- RECOVERY 6: Full System Reset (⚠️ DANGEROUS)
-- ============================================================================
-- Description: Reset entire pipeline to DISCOVERED state
-- Use Case: Complete system rebuild or catastrophic failure
-- Impact: CRITICAL - affects ALL records
-- WARNING: This will discard all progress!
-- ============================================================================

\echo 'RECOVERY 6: ⚠️  FULL SYSTEM RESET - This will discard all progress!'
\echo 'Press Ctrl+C to cancel, or wait 5 seconds to continue...'
\select pg_sleep(5);

BEGIN;

-- Confirmation prompt
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM match_pipeline_state LIMIT 1) THEN
        RAISE NOTICE 'Resetting all pipeline states to DISCOVERED';
    END IF;
END $$;

-- Reset all to DISCOVERED
UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW();

-- Optionally: Clear temporal records (uncomment if needed)
-- DELETE FROM temporal_metric_records;

-- Optionally: Clear mappings (uncomment if needed)
-- DELETE FROM matches_mapping;

COMMIT;

-- Verify reset
SELECT 'RECOVERY 6 Complete' as status, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status;


-- ============================================================================
-- RECOVERY 7: Backup Before Recovery
-- ============================================================================
-- Description: Create timestamped backup before running recovery
-- Use Case: Safety measure before any recovery operation
-- ============================================================================

\echo 'RECOVERY 7: Creating pre-recovery backup...'

-- Create backup with timestamp
CREATE TABLE pipeline_state_backup_20260125 AS
SELECT * FROM match_pipeline_state;

-- Verify backup
SELECT 'RECOVERY 7 Complete' as status, COUNT(*) as backed_up_records
FROM pipeline_state_backup_20260125;


-- ============================================================================
-- RECOVERY 8: Restore from Backup
-- ============================================================================
-- Description: Restore pipeline state from backup
-- Use Case: Rollback after failed recovery attempt
-- ============================================================================

\echo 'RECOVERY 8: Restoring from backup...'

BEGIN;

-- Clear current state
TRUNCATE match_pipeline_state;

-- Restore from backup
INSERT INTO match_pipeline_state
SELECT * FROM pipeline_state_backup_20260125;

COMMIT;

-- Verify restore
SELECT 'RECOVERY 8 Complete' as status, status, COUNT(*) as count
FROM match_pipeline_state
GROUP BY status;


-- ============================================================================
-- DIAGNOSTIC QUERIES
-- ============================================================================
-- These queries help diagnose issues before running recovery
-- ============================================================================

\echo ''
\echo '=== DIAGNOSTIC QUERIES ==='
\echo ''

-- Diagnostic 1: Show state distribution
\echo 'Diagnostic 1: Pipeline State Distribution'
\echo '----------------------------------------'
SELECT status, COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM match_pipeline_state
GROUP BY status
ORDER BY status;

\echo ''

-- Diagnostic 2: Show stale records (not updated in 24 hours)
\echo 'Diagnostic 2: Stale Records (updated > 24h ago)'
\echo '-------------------------------------------------'
SELECT status, COUNT(*) as stale_count
FROM match_pipeline_state
WHERE updated_at < NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY status;

\echo ''

-- Diagnostic 3: Show failed records by league
\echo 'Diagnostic 3: Failed Records by League'
\echo '---------------------------------------'
SELECT m.league_name, COUNT(*) as failed_count
FROM match_pipeline_state mps
JOIN matches m ON mps.match_id = m.match_id
WHERE mps.status = 'FAILED'
GROUP BY m.league_name
ORDER BY failed_count DESC
LIMIT 10;

\echo ''

-- Diagnostic 4: Show temporal data quality
\echo 'Diagnostic 4: Temporal Data Quality'
\echo '-----------------------------------'
SELECT
    COUNT(*) as total_records,
    COUNT(CASE WHEN payout < 0.80 OR payout > 1.00 THEN 1 END) as payout_anomalies,
    COUNT(CASE WHEN value <= 1.0 OR value >= 100 THEN 1 END) as odds_anomalies,
    ROUND(AVG(payout), 4) as avg_payout
FROM temporal_metric_records;

\echo ''

-- Diagnostic 5: Show golden completeness
\echo 'Diagnostic 5: Golden Data Completeness'
\echo '---------------------------------------'
SELECT
    COUNT(*) as total_matches,
    COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as with_l2,
    COUNT(CASE WHEN EXISTS(
        SELECT 1 FROM temporal_metric_records tmr
        WHERE tmr.entity_id::varchar = m.match_id
        LIMIT 1
    ) THEN 1 END) as with_temporal,
    COUNT(CASE WHEN l2_raw_json IS NOT NULL AND EXISTS(
        SELECT 1 FROM temporal_metric_records tmr
        WHERE tmr.entity_id::varchar = m.match_id
        LIMIT 1
    ) THEN 1 END) as golden_complete
FROM matches m
WHERE m.match_date >= NOW() - INTERVAL '2 years';

\echo ''
\echo '=== END OF DIAGNOSTICS ==='
\echo ''


-- ============================================================================
-- USAGE NOTES
-- ============================================================================
--
-- To run a specific recovery, uncomment the desired section above
-- and run: psql -U football_user -d football_db -f v70_300_emergency_recovery.sql
--
-- To run multiple recoveries, separate them with \i commands:
--
--   psql -U football_user -d football_db << EOF
--   -- Recovery 1
--   BEGIN;
--   UPDATE match_pipeline_state SET status = 'DISCOVERED' WHERE status = 'FAILED';
--   COMMIT;
--
--   -- Recovery 4
--   DELETE FROM temporal_metric_records WHERE payout < 0.70 OR payout > 1.10;
--   EOF
--
-- ============================================================================
