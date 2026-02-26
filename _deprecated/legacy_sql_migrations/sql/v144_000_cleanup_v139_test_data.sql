-- V144.000: Cleanup V139 Residual Test Data (Simplified)
-- ========================================================
--
-- This script checks and removes any residual test data from V139.
-- Since entity_id is UUID type, we only check matches table for test signatures.
--
-- Usage:
--   psql -U football_user -d football_db -f scripts/sql/v144_000_cleanup_v139_test_data.sql
--

-- Start transaction for safety
BEGIN;

-- Step 1: Identify test data
DO $$
DECLARE
    test_match_count INTEGER;
BEGIN
    -- Count matches with test signatures
    SELECT COUNT(*)
    INTO test_match_count
    FROM matches
    WHERE league_name LIKE '%TEST%'
       OR home_team LIKE '%TEST%'
       OR away_team LIKE '%TEST%'
       OR season LIKE '%TEST%'
       OR match_id::text LIKE 'test%';

    IF test_match_count > 0 THEN
        RAISE NOTICE '[V144.000] Found % matches with test signatures', test_match_count;
    ELSE
        RAISE NOTICE '[V144.000] ✅ No test data found - Database is clean';
    END IF;
END $$;

-- Step 2: Delete test data (if any)
-- First delete related temporal records (via entity_id)
-- Note: entity_id is UUID, so we can only match via match_id from matches table
-- Since temporal_metric_records uses entity_id as UUID, we skip direct matching

-- Delete odds data for test matches
DELETE FROM metrics_multi_source_data
WHERE match_id IN (
    SELECT match_id
    FROM matches
    WHERE league_name LIKE '%TEST%'
       OR home_team LIKE '%TEST%'
       OR away_team LIKE '%TEST%'
       OR season LIKE '%TEST%'
       OR match_id::text LIKE 'test%'
);

-- Delete mapping data for test matches
DELETE FROM matches_mapping
WHERE fotmob_id IN (
    SELECT match_id
    FROM matches
    WHERE league_name LIKE '%TEST%'
       OR home_team LIKE '%TEST%'
       OR away_team LIKE '%TEST%'
       OR season LIKE '%TEST%'
       OR match_id::text LIKE 'test%'
);

-- Delete test matches
DELETE FROM matches
WHERE league_name LIKE '%TEST%'
   OR home_team LIKE '%TEST%'
   OR away_team LIKE '%TEST%'
   OR season LIKE '%TEST%'
   OR match_id::text LIKE 'test%';

-- Commit transaction
COMMIT;

-- Final verification
DO $$
DECLARE
    remaining_tests INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO remaining_tests
    FROM matches
    WHERE league_name LIKE '%TEST%'
       OR home_team LIKE '%TEST%'
       OR away_team LIKE '%TEST%'
       OR season LIKE '%TEST%'
       OR match_id::text LIKE 'test%';

    IF remaining_tests = 0 THEN
        RAISE NOTICE '[V144.000] ✅ CLEANUP COMPLETE - Database is clean';
    ELSE
        RAISE NOTICE '[V144.000] ⚠️  % test matches remain', remaining_tests;
    END IF;
END $$;

-- Final status report
SELECT
    'V144.000 CLEANUP STATUS' as status,
    COUNT(*) as total_matches_remaining,
    COUNT(*) FILTER (WHERE l3_extraction_status = 'PENDING') as pending_matches
FROM matches
WHERE league_name NOT LIKE '%TEST%'
   AND home_team NOT LIKE '%TEST%'
   AND away_team NOT LIKE '%TEST%';
