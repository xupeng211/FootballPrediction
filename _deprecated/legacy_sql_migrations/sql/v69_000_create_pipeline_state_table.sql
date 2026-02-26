-- ============================================================================
-- V69.000 - Pipeline State Table Migration
-- ============================================================================
--
-- Creates the match_pipeline_state table for tracking the automated
-- data flow pipeline status.
--
-- @version V69.000
-- @author Principal Systems Integration Engineer
-- @since 2026-01-25
--
-- ============================================================================

-- Create match_pipeline_state table
CREATE TABLE IF NOT EXISTS match_pipeline_state (
    match_id VARCHAR(50) PRIMARY KEY,

    -- Current status in the pipeline
    -- DISCOVERED: Initial state, match indexed in match_search_queue
    -- ENRICHED: L2 data (xG, lineups, ratings) collected
    -- MAPPED: Bridge mapping to oddsportal completed
    -- HARVESTED: Temporal odds data collected
    -- FAILED: Processing failed at some stage
    status VARCHAR(20) NOT NULL DEFAULT 'DISCOVERED',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Foreign key to matches table
    CONSTRAINT fk_pipeline_match
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    -- Validate status values
    CONSTRAINT valid_status
        CHECK (status IN ('DISCOVERED', 'ENRICHED', 'MAPPED', 'HARVESTED', 'FAILED'))
);

-- ============================================================================
-- COMMENT
-- ============================================================================

COMMENT ON TABLE match_pipeline_state IS
    'V69.000: Tracks the automated pipeline status for each match';

COMMENT ON COLUMN match_pipeline_state.match_id IS
    'Foreign key reference to matches.match_id';

COMMENT ON COLUMN match_pipeline_state.status IS
    'Current pipeline status: DISCOVERED, ENRICHED, MAPPED, HARVESTED, FAILED';

COMMENT ON COLUMN match_pipeline_state.created_at IS
    'Timestamp when the record was first created';

COMMENT ON COLUMN match_pipeline_state.updated_at IS
    'Timestamp of the last status update';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for querying matches by status and age
CREATE INDEX idx_pipeline_status_updated
ON match_pipeline_state(status, updated_at DESC);

-- Index for querying stale DISCOVERED records
CREATE INDEX idx_pipeline_discovered
ON match_pipeline_state(status, updated_at)
WHERE status = 'DISCOVERED';

-- Index for querying stale ENRICHED records (need bridge)
CREATE INDEX idx_pipeline_enriched
ON match_pipeline_state(status, updated_at)
WHERE status = 'ENRICHED';

-- Index for querying stale MAPPED records (need harvest)
CREATE INDEX idx_pipeline_mapped
ON match_pipeline_state(status, updated_at)
WHERE status = 'MAPPED';

-- ============================================================================
-- TRIGGER: Auto-update updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_pipeline_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_pipeline_state_updated_at
BEFORE UPDATE ON match_pipeline_state
FOR EACH ROW
EXECUTE FUNCTION update_pipeline_state_updated_at();

-- ============================================================================
-- TRIGGER: Auto-create state on new matches
-- ============================================================================

-- Automatically create DISCOVERED state for new matches
CREATE OR REPLACE FUNCTION create_match_pipeline_state()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO match_pipeline_state (match_id, status)
    VALUES (NEW.match_id, 'DISCOVERED')
    ON CONFLICT (match_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_match_pipeline_state
AFTER INSERT ON matches
FOR EACH ROW
EXECUTE FUNCTION create_match_pipeline_state();

-- ============================================================================
-- VIEWS: Pipeline Monitoring
-- ============================================================================

-- View for monitoring pipeline health
CREATE OR REPLACE VIEW v_pipeline_health AS
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,
    MIN(updated_at) as oldest_update,
    MAX(updated_at) as newest_update,
    NOW() - MAX(updated_at) as time_since_last_update
FROM match_pipeline_state
GROUP BY status
ORDER BY
    CASE status
        WHEN 'DISCOVERED' THEN 1
        WHEN 'ENRICHED' THEN 2
        WHEN 'MAPPED' THEN 3
        WHEN 'HARVESTED' THEN 4
        WHEN 'FAILED' THEN 5
    END;

COMMENT ON VIEW v_pipeline_health IS
    'V69.000: Real-time pipeline health monitoring view';

-- ============================================================================
-- FUNCTIONS: Status Transition
-- ============================================================================

-- Function to transition match to next status
CREATE OR REPLACE FUNCTION transition_pipeline_status(
    p_match_id VARCHAR(50),
    p_new_status VARCHAR(20)
) RETURNS BOOLEAN AS $$
DECLARE
    current_status VARCHAR(20);
BEGIN
    -- Get current status
    SELECT status INTO current_status
    FROM match_pipeline_state
    WHERE match_id = p_match_id;

    IF NOT FOUND THEN
        -- Create new record with DISCOVERED status
        INSERT INTO match_pipeline_state (match_id, status)
        VALUES (p_match_id, 'DISCOVERED');
        current_status := 'DISCOVERED';
    END IF;

    -- Validate transition
    IF p_new_status = 'FAILED' THEN
        -- Always allow transition to FAILED
        UPDATE match_pipeline_state
        SET status = 'FAILED'
        WHERE match_id = p_match_id;
        RETURN TRUE;
    END IF;

    -- Validate forward progression
    IF current_status = 'DISCOVERED' AND p_new_status IN ('ENRICHED', 'FAILED') THEN
        UPDATE match_pipeline_state SET status = p_new_status WHERE match_id = p_match_id;
        RETURN TRUE;
    ELSIF current_status = 'ENRICHED' AND p_new_status IN ('MAPPED', 'FAILED') THEN
        UPDATE match_pipeline_state SET status = p_new_status WHERE match_id = p_match_id;
        RETURN TRUE;
    ELSIF current_status = 'MAPPED' AND p_new_status IN ('HARVESTED', 'FAILED') THEN
        UPDATE match_pipeline_state SET status = p_new_status WHERE match_id = p_match_id;
        RETURN TRUE;
    ELSE
        -- Invalid transition
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION transition_pipeline_status IS
    'V69.000: Safely transition match to next pipeline status with validation';

-- ============================================================================
-- FUNCTIONS: Stale Record Detection
-- ============================================================================

-- Get matches needing L2 enrichment (DISCOVERED for > 1 hour)
CREATE OR REPLACE FUNCTION get_stale_discovered(limit INTEGER DEFAULT 50)
RETURNS TABLE (
    match_id VARCHAR(50),
    league_name VARCHAR(255),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    match_date TIMESTAMP,
    status_age INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.match_id,
        m.league_name,
        m.home_team,
        m.away_team,
        m.match_date,
        NOW() - ps.updated_at as status_age
    FROM match_pipeline_state ps
    JOIN matches m ON m.match_id = ps.match_id
    WHERE ps.status = 'DISCOVERED'
      AND ps.updated_at < NOW() - INTERVAL '1 hour'
      AND m.l2_raw_json IS NULL
      AND m.match_date >= NOW() - INTERVAL '6 months'
    ORDER BY ps.updated_at ASC
    LIMIT limit;
END;
$$ LANGUAGE plpgsql;

-- Get matches needing bridge mapping (ENRICHED for > 30 minutes)
CREATE OR REPLACE FUNCTION get_stale_enriched(limit INTEGER DEFAULT 100)
RETURNS TABLE (
    match_id VARCHAR(50),
    league_name VARCHAR(255),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    match_date TIMESTAMP,
    status_age INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.match_id,
        m.league_name,
        m.home_team,
        m.away_team,
        m.match_date,
        NOW() - ps.updated_at as status_age
    FROM match_pipeline_state ps
    JOIN matches m ON m.match_id = ps.match_id
    LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
    WHERE ps.status = 'ENRICHED'
      AND ps.updated_at < NOW() - INTERVAL '30 minutes'
      AND mm.fotmob_id IS NULL
      AND m.match_date >= NOW() - INTERVAL '6 months'
    ORDER BY ps.updated_at ASC
    LIMIT limit;
END;
$$ LANGUAGE plpgsql;

-- Get matches needing odds harvest (MAPPED for > 24 hours)
CREATE OR REPLACE FUNCTION get_stale_mapped(limit INTEGER DEFAULT 20)
RETURNS TABLE (
    match_id VARCHAR(50),
    oddsportal_url TEXT,
    league_name VARCHAR(255),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    match_date TIMESTAMP,
    status_age INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mm.fotmob_id,
        mm.oddsportal_url,
        m.league_name,
        m.home_team,
        m.away_team,
        m.match_date,
        NOW() - ps.updated_at as status_age
    FROM match_pipeline_state ps
    JOIN matches_mapping mm ON ps.match_id = mm.fotmob_id
    JOIN matches m ON mm.fotmob_id = m.match_id
    LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = mm.fotmob_id
    WHERE ps.status = 'MAPPED'
      AND ps.updated_at < NOW() - INTERVAL '24 hours'
      AND (tmr.entity_id IS NULL OR tmr.occurred_at < NOW() - INTERVAL '24 hours')
      AND m.match_date >= NOW() + INTERVAL '48 hours'
      AND m.match_date <= NOW() + INTERVAL '7 days'
    ORDER BY
        CASE WHEN m.league_name IN (
            'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1'
        ) THEN 0 ELSE 1 END,
        m.match_date ASC
    LIMIT limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BACKFILL: Initialize existing matches
-- ============================================================================

-- Backfill existing matches with appropriate initial status
INSERT INTO match_pipeline_state (match_id, status)
SELECT
    match_id,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM temporal_metric_records tmr
            WHERE tmr.entity_id = m.match_id
        ) THEN 'HARVESTED'
        WHEN EXISTS (
            SELECT 1 FROM matches_mapping mm
            WHERE mm.fotmob_id = m.match_id
        ) THEN 'MAPPED'
        WHEN m.l2_raw_json IS NOT NULL THEN 'ENRICHED'
        ELSE 'DISCOVERED'
    END
FROM matches m
ON CONFLICT (match_id) DO NOTHING;

-- Log backfill results
DO $$
DECLARE
    v_total INTEGER;
    v_discovered INTEGER;
    v_enriched INTEGER;
    v_mapped INTEGER;
    v_harvested INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total FROM match_pipeline_state;
    SELECT COUNT(*) INTO v_discovered FROM match_pipeline_state WHERE status = 'DISCOVERED';
    SELECT COUNT(*) INTO v_enriched FROM match_pipeline_state WHERE status = 'ENRICHED';
    SELECT COUNT(*) INTO v_mapped FROM match_pipeline_state WHERE status = 'MAPPED';
    SELECT COUNT(*) INTO v_harvested FROM match_pipeline_state WHERE status = 'HARVESTED';

    RAISE NOTICE '=== V69.000 Pipeline State Backfill ===';
    RAISE NOTICE 'Total matches initialized: %', v_total;
    RAISE NOTICE '  DISCOVERED: % (%)', v_discovered, ROUND(100.0 * v_discovered / v_total, 2);
    RAISE NOTICE '  ENRICHED: % (%)', v_enriched, ROUND(100.0 * v_enriched / v_total, 2);
    RAISE NOTICE '  MAPPED: % (%)', v_mapped, ROUND(100.0 * v_mapped / v_total, 2);
    RAISE NOTICE '  HARVESTED: % (%)', v_harvested, ROUND(100.0 * v_harvested / v_total, 2);
    RAISE NOTICE '====================================';
END $$;

-- ============================================================================
-- GRANT PERMISSIONS (for application user)
-- ============================================================================

-- Grant permissions to football_user
GRANT SELECT, INSERT, UPDATE, DELETE ON match_pipeline_state TO football_user;
GRANT SELECT, UPDATE ON SEQUENCE match_pipeline_state_match_id_seq TO football_user;
GRANT SELECT ON v_pipeline_health TO football_user;
GRANT EXECUTE ON FUNCTION transition_pipeline_status TO football_user;
GRANT EXECUTE ON FUNCTION get_stale_discovered TO football_user;
GRANT EXECUTE ON FUNCTION get_stale_enriched TO football_user;
GRANT EXECUTE ON FUNCTION get_stale_mapped TO football_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify table creation
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_name = 'match_pipeline_state') THEN
        RAISE NOTICE '✅ Table match_pipeline_state created successfully';
    ELSE
        RAISE EXCEPTION '❌ Table match_pipeline_state creation failed';
    END IF;
END $$;

-- Verify indexes
DO $$
DECLARE
    v_index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_index_count
    FROM pg_indexes
    WHERE tablename = 'match_pipeline_state';

    RAISE NOTICE '✅ Created % indexes on match_pipeline_state', v_index_count;
END $$;

-- Verify triggers
DO $$
DECLARE
    v_trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_trigger_count
    FROM information_schema.triggers
    WHERE event_object_table = 'match_pipeline_state';

    RAISE NOTICE '✅ Created % triggers on match_pipeline_state', v_trigger_count;
END $$;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
