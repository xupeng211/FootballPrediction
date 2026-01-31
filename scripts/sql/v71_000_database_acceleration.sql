-- ============================================================================
-- V71.000 - Database Acceleration & Stress Test Preparation
-- ============================================================================
--
-- This script creates optimized indexes and tables for:
-- - Phase 1: "Golden Table" fusion query acceleration
-- - Phase 3: 100-match stress test monitoring
--
-- @file v71_000_database_acceleration.sql
-- @version V71.000
-- @since 2026-01-25
--
-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
--
-- Execute with:
--    psql -h 172.25.16.1 -U football_user -d football_db -f v71_000_database_acceleration.sql
--    OR
--    docker exec -i football_db psql -U football_user -d football_db < v71_000_database_acceleration.sql
--
-- ============================================================================

\echo 'V71.000: Starting database acceleration...'

-- ============================================================================
-- PART 1: Create match_pipeline_state table (currently missing)
-- ============================================================================

\echo 'Part 1: Creating match_pipeline_state table...'

CREATE TABLE IF NOT EXISTS match_pipeline_state (
    match_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'DISCOVERED',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add check constraint for valid status values
ALTER TABLE match_pipeline_state
ADD CONSTRAINT valid_pipeline_status
CHECK (status IN ('DISCOVERED', 'ENRICHED', 'MAPPED', 'HARVESTED', 'FAILED'));

-- Add comment for documentation
COMMENT ON TABLE match_pipeline_state IS 'V69.000 Pipeline state tracking for matches';
COMMENT ON COLUMN match_pipeline_state.match_id IS 'Foreign key reference to matches.match_id';
COMMENT ON COLUMN match_pipeline_state.status IS 'Pipeline state: DISCOVERED → ENRICHED → MAPPED → HARVESTED → FAILED';
COMMENT ON COLUMN match_pipeline_state.updated_at IS 'Last state transition timestamp';

-- ============================================================================
-- PART 2: Golden Table Fusion Query Indexes
-- ============================================================================

\echo 'Part 2: Creating golden table fusion indexes...'

-- Index 2A: matches composite index for L2 + temporal join
-- Supports: SELECT FROM matches m LEFT JOIN temporal_metric_records tmr ON tmr.entity_id::varchar = m.match_id
CREATE INDEX IF NOT EXISTS idx_matches_golden_lookup
ON matches (match_id, league_name, match_date)
WHERE l2_raw_json IS NOT NULL;

-- Index 2B: matches_mapping composite index for bridge mapping queries
-- Supports: SELECT FROM matches_mapping mm JOIN matches m ON mm.fotmob_id = m.match_id
CREATE INDEX IF NOT EXISTS idx_matches_mapping_bridge_lookup
ON matches_mapping (fotmob_id, oddsportal_hash, status)
WHERE oddsportal_url IS NOT NULL;

-- Index 2C: temporal_metric_records composite index for entity-time queries
-- (Already exists as idx_temporal_query, but adding a covering index for better performance)
CREATE INDEX IF NOT EXISTS idx_temporal_golden_covering
ON temporal_metric_records (entity_id, occurred_at, metric_type, dimension)
WHERE payout IS NOT NULL;

-- Index 2D: match_pipeline_state status scan index for sentinel
CREATE INDEX IF NOT EXISTS idx_pipeline_state_status_scan
ON match_pipeline_state (status, updated_at);

-- Index 2E: match_pipeline_state stale record detection
CREATE INDEX IF NOT EXISTS idx_pipeline_state_stale_detection
ON match_pipeline_state (updated_at)
WHERE status IN ('ENRICHED', 'MAPPED');

-- ============================================================================
-- PART 3: Performance Monitoring Views
-- ============================================================================

\echo 'Part 3: Creating performance monitoring views...'

-- View 3A: Golden entities completeness view
CREATE OR REPLACE VIEW v_golden_entities_completeness AS
SELECT
    m.match_id,
    m.match_date,
    m.league_name,
    m.home_team,
    m.away_team,
    -- Index check
    m.match_id IS NOT NULL as has_index,
    -- L2 check
    m.l2_raw_json IS NOT NULL as has_l2,
    -- Temporal check (cast entity_id to varchar for comparison)
    EXISTS(
        SELECT 1 FROM temporal_metric_records tmr
        WHERE tmr.entity_id::varchar = m.match_id
        LIMIT 1
    ) as has_temporal,
    -- Bridge mapping check
    mm.oddsportal_url IS NOT NULL as has_bridge_mapping,
    -- Pipeline state
    COALESCE(mps.status, 'DISCOVERED') as pipeline_status
FROM matches m
LEFT JOIN matches_mapping mm ON mm.fotmob_id = m.match_id
LEFT JOIN match_pipeline_state mps ON mps.match_id = m.match_id
WHERE m.match_date >= NOW() - INTERVAL '2 years';

COMMENT ON VIEW v_golden_entities_completeness IS 'V71.000: Golden entities completeness monitoring view';

-- View 3B: Pipeline state distribution view
CREATE OR REPLACE VIEW v_pipeline_state_distribution AS
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,
    COUNT(*) FILTER (WHERE updated_at < NOW() - INTERVAL '24 hours') as stale_count
FROM match_pipeline_state
GROUP BY status
ORDER BY status;

COMMENT ON VIEW v_pipeline_state_distribution IS 'V71.000: Pipeline state distribution for sentinel monitoring';

-- ============================================================================
-- PART 4: Query Performance Test
-- ============================================================================

\echo 'Part 4: Testing query performance...'

\timing on

-- Test 4A: Golden entities count (should be < 100ms)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT COUNT(*) as golden_count
FROM v_golden_entities_completeness
WHERE has_index = true
  AND has_l2 = true
  AND has_temporal = true;

-- Test 4B: Pipeline state distribution (should be < 50ms)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM v_pipeline_state_distribution;

-- Test 4C: Bridge mapping lookup (should be < 50ms)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT COUNT(*)
FROM matches_mapping mm
JOIN matches m ON mm.fotmob_id = m.match_id
WHERE mm.status = 'approved'
  AND m.league_name = 'Premier League'
  AND m.season = '2024/2025';

\timing off

-- ============================================================================
-- PART 5: Verify Index Creation
-- ============================================================================

\echo ''
\echo '=== V71.000 Index Verification ==='
\echo ''

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%golden%'
   OR indexname LIKE 'idx_%bridge%'
   OR indexname LIKE 'idx_%pipeline%'
ORDER BY tablename, indexname;

\echo ''
\echo '=== V71.000: Database acceleration complete ==='
\echo ''

-- ============================================================================
-- PART 6: Stress Test Support Queries
-- ============================================================================

\echo 'Stress Test Support Queries Prepared:'
\echo '  - Q1: SELECT * FROM v_golden_entities_completeness LIMIT 100;'
\echo '  - Q2: SELECT * FROM v_pipeline_state_distribution;'
\echo '  - Q3: SELECT COUNT(*) FROM match_pipeline_state WHERE status = '\''FAILED'\'';'
\echo ''
