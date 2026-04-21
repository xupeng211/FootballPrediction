-- =============================================================================
-- V12.4 Database Migration: Create matches_oddsportal_mapping
-- =============================================================================
-- 目标:
--   将 Recon / OddsPortal 映射表纳入正式 migration 蓝图，确保空库冷启动时
--   能通过代码完整恢复 RECON 所需的核心结构。
-- =============================================================================

CREATE TABLE IF NOT EXISTS matches_oddsportal_mapping (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    oddsportal_hash VARCHAR(8) NOT NULL,
    full_url TEXT NOT NULL,
    season VARCHAR(20) NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    match_confidence NUMERIC(6, 4),
    mapping_method VARCHAR(50),
    is_reversed BOOLEAN DEFAULT FALSE,
    candidate_name VARCHAR(255),
    is_evidence_only BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    harvested_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(match_id, season),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'harvested', 'failed', 'skipped', 'processing')),
    CONSTRAINT valid_method CHECK (
        mapping_method IN (
            'exact',
            'fuzzy',
            'manual',
            'unknown',
            'exact_kickoff_tolerance',
            'home_date_fill',
            'hash_lock',
            'sequential_hash_rollover',
            'set_closure',
            'set_reconciliation',
            'recon_matrix',
            'protocol_extract',
            'dictionary',
            'season_mirror',
            'semantic',
            'V5.5_HARVESTER',
            'v41_186_auto'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_mapping_season
ON matches_oddsportal_mapping(season);

CREATE INDEX IF NOT EXISTS idx_mapping_status
ON matches_oddsportal_mapping(status);

CREATE INDEX IF NOT EXISTS idx_mapping_league
ON matches_oddsportal_mapping(league_name);

CREATE INDEX IF NOT EXISTS idx_mapping_hash
ON matches_oddsportal_mapping(oddsportal_hash);

CREATE INDEX IF NOT EXISTS idx_mapping_evidence_only
ON matches_oddsportal_mapping(is_evidence_only);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique
ON matches_oddsportal_mapping(season, oddsportal_hash);

CREATE INDEX IF NOT EXISTS idx_mapping_pending
ON matches_oddsportal_mapping(status, retry_count)
WHERE status IN ('pending', 'failed') AND retry_count < 3;

CREATE OR REPLACE FUNCTION update_mapping_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_mapping_timestamp ON matches_oddsportal_mapping;
CREATE TRIGGER trigger_update_mapping_timestamp
    BEFORE UPDATE ON matches_oddsportal_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_mapping_updated_at();

CREATE OR REPLACE VIEW v_mapping_stats AS
SELECT
    season,
    league_name,
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'harvested') as harvested,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
    COUNT(*) FILTER (WHERE status = 'processing') as processing,
    ROUND(COUNT(*) FILTER (WHERE status = 'harvested') * 100.0 / NULLIF(COUNT(*), 0), 2) as harvest_rate
FROM matches_oddsportal_mapping
GROUP BY season, league_name
ORDER BY season DESC, league_name;

COMMENT ON TABLE matches_oddsportal_mapping IS
'V12.4: OddsPortal 映射表，保存 match_id 与 OddsPortal canonical identity 的正式绑定';

COMMENT ON COLUMN matches_oddsportal_mapping.is_evidence_only IS
'V12.4: true 表示仅作为证据占位，false 表示正式 mapping';
