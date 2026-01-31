-- V41.273 "Total Vision" - Lineup Feature Extension
-- ===================================================================
--
-- This migration adds the match_lineups table to store starting XI
-- and missing players data for AI prediction features (195+ dimensions).
--
-- Author: Senior AI Data Scientist
-- Date: 2026-01-20
-- Version: V41.273 "Total Vision"

BEGIN;

-- ============================================================================
-- Create match_lineups table
-- ============================================================================

CREATE TABLE IF NOT EXISTS match_lineups (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- Home team lineup
    home_formation VARCHAR(10),
    home_starting_xi JSONB,
    home_missing_players JSONB,

    -- Away team lineup
    away_formation VARCHAR(10),
    away_starting_xi JSONB,
    away_missing_players JSONB,

    -- Metadata
    source VARCHAR(50) DEFAULT 'FotMob',
    source_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Full-text search for quick lookups
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(home_formation, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(away_formation, '')), 'A')
    ) STORED,

    -- Constraints
    CONSTRAINT unique_match_lineup UNIQUE (match_id)
);

-- ============================================================================
-- Create indexes for performance
-- ============================================================================

-- Primary lookup index
CREATE INDEX IF NOT EXISTS idx_lineups_match_id ON match_lineups(match_id);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_lineups_search ON match_lineups USING GIN(search_vector);

-- Formation filter index
CREATE INDEX IF NOT EXISTS idx_lineups_home_formation ON match_lineups(home_formation);
CREATE INDEX IF NOT EXISTS idx_lineups_away_formation ON match_lineups(away_formation);

-- Source tracking index
CREATE INDEX IF NOT EXISTS idx_lineups_source ON match_lineups(source);

-- ============================================================================
-- Add comments for documentation
-- ============================================================================

COMMENT ON TABLE match_lineups IS '
V41.273: Match lineups and missing players data for AI prediction features.

Stores starting XI formations and player information for both home and away teams.
This data enriches the feature set to 195+ dimensions for improved prediction accuracy.

JSONB Structure:
- home_starting_xi: [{"player_id": "...", "name": "...", "position": "...", "shirt_number": N, "rating": N}, ...]
- home_missing_players: [{"player_id": "...", "name": "...", "reason": "..."}, ...]
- away_starting_xi: Same structure as home
- away_missing_players: Same structure as home

Example:
{
  "home_formation": "4-3-3",
  "home_starting_xi": [
    {"player_id": "12345", "name": "Ederson", "position": "GK", "shirt_number": 31, "rating": 7.2},
    {"player_id": "12346", "name": "Kyle Walker", "position": "RB", "shirt_number": 2, "rating": 6.8},
    ...
  ],
  "home_missing_players": [
    {"player_id": "12350", "name": "Kevin De Bruyne", "reason": "Injured"},
    ...
  ]
}
';

COMMENT ON COLUMN match_lineups.home_formation IS 'Home team formation (e.g., "4-3-3", "4-4-2")';
COMMENT ON COLUMN match_lineups.home_starting_xi IS 'Home team starting XI with player details';
COMMENT ON COLUMN match_lineups.home_missing_players IS 'Home team missing/suspended players';
COMMENT ON COLUMN match_lineups.away_formation IS 'Away team formation (e.g., "4-3-3", "4-4-2")';
COMMENT ON COLUMN match_lineups.away_starting_xi IS 'Away team starting XI with player details';
COMMENT ON COLUMN match_lineups.away_missing_players IS 'Away team missing/suspended players';
COMMENT ON COLUMN match_lineups.source IS 'Data source (FotMob, API, etc.)';
COMMENT ON COLUMN match_lineups.source_updated_at IS 'Timestamp when source data was last updated';

-- ============================================================================
-- Create trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_lineups_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_lineups_updated_at ON match_lineups;
CREATE TRIGGER trigger_update_lineups_updated_at
    BEFORE UPDATE ON match_lineups
    FOR EACH ROW
    EXECUTE FUNCTION update_lineups_updated_at();

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== V41.273 Lineup Table Created ===';
    RAISE NOTICE 'Table: match_lineups';
    RAISE NOTICE 'Indexes: 5 (match_id, search, formations, source)';
    RAISE NOTICE 'Trigger: updated_at auto-update';
    RAISE NOTICE 'Status: ACTIVE';
END $$;

-- Verify the table was created
SELECT
    table_name,
    (SELECT count(*) FROM information_schema.columns WHERE table_name = 'match_lineups') as column_count
FROM information_schema.tables
WHERE table_name = 'match_lineups';

COMMIT;
