-- ============================================================================
-- V49.100 Database Audit Verification SQL
-- ============================================================================
--
-- Purpose: Verify that 5-node scaling is operational by checking
--          temporal_metric_records table for 5 different provider identifiers
--
-- Usage: psql -h <host> -U <user> -d football_db -f v49_100_audit.sql
--
-- @module v49_100_audit
-- @version V49.100
-- @since 2026-01-24
-- ============================================================================

\echo '=========================================='
\echo 'V49.100 Scaling Audit Report'
\echo '=========================================='
\echo ''

-- ============================================================================
-- 1. Check provider count per entity
-- ============================================================================
\echo '[1] Provider Count Distribution'
\echo '----------------------------------------'

SELECT
    entity_id,
    COUNT(DISTINCT provider_name) as provider_count,
    STRING_AGG(DISTINCT provider_name, ', ' ORDER BY provider_name) as providers
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
GROUP BY entity_id
ORDER BY provider_count DESC, entity_id
LIMIT 10;

\echo ''

-- ============================================================================
-- 2. Verify 5-node coverage for specific entity
-- ============================================================================
\echo '[2] Expected 5-Node Providers'
\echo '----------------------------------------'

SELECT DISTINCT
    provider_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT dimension) as dimensions
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
  AND provider_name IN ('pinnacle', 'bet365', 'vendor-wh', 'vendor-bw', 'vendor-188')
GROUP BY provider_name
ORDER BY provider_name;

\echo ''

-- ============================================================================
-- 3. Dimension coverage (Home/Draw/Away) per provider
-- ============================================================================
\echo '[3] Dimension Coverage (Home/Draw/Away)'
\echo '----------------------------------------'

SELECT
    provider_name,
    dimension,
    COUNT(*) as records,
    MIN(occurred_at) as earliest,
    MAX(occurred_at) as latest
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
GROUP BY provider_name, dimension
ORDER BY provider_name, dimension;

\echo ''

-- ============================================================================
-- 4. Temporal points per provider
-- ============================================================================
\echo '[4] Temporal Points per Provider'
\echo '----------------------------------------'

SELECT
    provider_name,
    COUNT(DISTINCT sequence) as temporal_points,
    MIN(sequence) as min_seq,
    MAX(sequence) as max_seq
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
GROUP BY provider_name
ORDER BY provider_name;

\echo ''

-- ============================================================================
-- 5. Payout validation (data quality check)
-- ============================================================================
\echo '[5] Payout Validation (Quality Check)'
\echo '----------------------------------------'

SELECT
    provider_name,
    COUNT(*) as records,
    COUNT(payout) as with_payout,
    ROUND(AVG(payout)::numeric, 4) as avg_payout,
    ROUND(MIN(payout)::numeric, 4) as min_payout,
    ROUND(MAX(payout)::numeric, 4) as max_payout
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
  AND payout IS NOT NULL
GROUP BY provider_name
ORDER BY provider_name;

\echo ''

-- ============================================================================
-- 6. Acceptance Criteria Summary
-- ============================================================================
\echo '=========================================='
\echo 'V49.100 Acceptance Criteria Summary'
\echo '=========================================='

SELECT
    'Target: 5 providers' as criteria,
    COUNT(DISTINCT provider_name) as actual_value,
    CASE WHEN COUNT(DISTINCT provider_name) >= 5 THEN 'PASS' ELSE 'FAIL' END as status
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'

UNION ALL

SELECT
    'Target: 3 dimensions (home/draw/away)',
    COUNT(DISTINCT dimension),
    CASE WHEN COUNT(DISTINCT dimension) >= 3 THEN 'PASS' ELSE 'FAIL' END
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'

UNION ALL

SELECT
    'Target: Payout calculation present',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END
FROM temporal_metric_records
WHERE metric_type = 'temporal_odds_1x2_full'
  AND payout IS NOT NULL;

\echo ''
\echo '=========================================='
\echo 'V49.100 Audit Complete'
\echo '=========================================='
