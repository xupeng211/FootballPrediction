-- V26.6: Create football calendar target registry tables for FotMob long-run collection.
-- lifecycle: permanent
-- Scope: target registry schema only. No source access. No seed data. No raw JSON storage.

CREATE TABLE IF NOT EXISTS football_teams (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'fotmob',
    source_team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    team_type TEXT NOT NULL,
    country TEXT,
    gender TEXT DEFAULT 'men',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_teams_source_team UNIQUE (source, source_team_id),
    CONSTRAINT ck_football_teams_team_type CHECK (team_type IN ('club', 'national'))
);

CREATE TABLE IF NOT EXISTS football_competitions (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'fotmob',
    source_competition_id TEXT NOT NULL,
    competition_name TEXT NOT NULL,
    competition_type TEXT NOT NULL,
    country TEXT,
    confederation TEXT,
    tier INTEGER,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_competitions_source_competition UNIQUE (source, source_competition_id),
    CONSTRAINT ck_football_competitions_competition_type CHECK (
        competition_type IN (
            'league',
            'domestic_cup',
            'continental_club',
            'international_tournament',
            'international_qualifier',
            'nations_league',
            'friendly',
            'super_cup',
            'other'
        )
    )
);

CREATE TABLE IF NOT EXISTS football_competition_editions (
    id BIGSERIAL PRIMARY KEY,
    competition_id BIGINT NOT NULL REFERENCES football_competitions(id),
    season TEXT NOT NULL,
    edition_name TEXT,
    start_date DATE,
    end_date DATE,
    calendar_type TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_competition_editions_competition_season UNIQUE (competition_id, season)
);

CREATE TABLE IF NOT EXISTS football_team_competition_participation (
    id BIGSERIAL PRIMARY KEY,
    team_id BIGINT NOT NULL REFERENCES football_teams(id),
    competition_id BIGINT NOT NULL REFERENCES football_competitions(id),
    edition_id BIGINT NOT NULL REFERENCES football_competition_editions(id),
    participation_state TEXT NOT NULL DEFAULT 'unknown',
    qualification_source TEXT,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_team_competition_participation UNIQUE (team_id, competition_id, edition_id),
    CONSTRAINT ck_football_team_competition_participation_state CHECK (
        participation_state IN ('expected', 'confirmed', 'eliminated', 'completed', 'unknown')
    )
);

CREATE TABLE IF NOT EXISTS football_match_targets (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'fotmob',
    source_match_id TEXT NOT NULL,
    competition_id BIGINT REFERENCES football_competitions(id),
    edition_id BIGINT REFERENCES football_competition_editions(id),
    match_date TIMESTAMPTZ,
    home_team_id BIGINT REFERENCES football_teams(id),
    away_team_id BIGINT REFERENCES football_teams(id),
    match_status TEXT,
    target_state TEXT NOT NULL DEFAULT 'discovered',
    priority INTEGER NOT NULL DEFAULT 100,
    discovery_source TEXT,
    source_url TEXT,
    raw_json_status TEXT,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error_code TEXT,
    last_error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_match_targets_source_match UNIQUE (source, source_match_id),
    CONSTRAINT ck_football_match_targets_target_state CHECK (
        target_state IN (
            'discovered',
            'pending_raw_fetch',
            'raw_fetched',
            'raw_json_stored',
            'blocked',
            'failed',
            'retired'
        )
    ),
    CONSTRAINT ck_football_match_targets_attempt_count CHECK (attempt_count >= 0)
);

CREATE TABLE IF NOT EXISTS football_match_target_teams (
    id BIGSERIAL PRIMARY KEY,
    match_target_id BIGINT NOT NULL REFERENCES football_match_targets(id),
    team_id BIGINT NOT NULL REFERENCES football_teams(id),
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_match_target_teams_target_team_role UNIQUE (match_target_id, team_id, role),
    CONSTRAINT ck_football_match_target_teams_role CHECK (role IN ('home', 'away', 'participant'))
);

CREATE TABLE IF NOT EXISTS football_source_identities (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id BIGINT,
    source_entity_id TEXT NOT NULL,
    source_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_football_source_identities_source_entity UNIQUE (source, entity_type, source_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_football_teams_team_type
    ON football_teams (team_type);

CREATE INDEX IF NOT EXISTS idx_football_teams_country
    ON football_teams (country);

CREATE INDEX IF NOT EXISTS idx_football_teams_active
    ON football_teams (active);

CREATE INDEX IF NOT EXISTS idx_football_competitions_type
    ON football_competitions (competition_type);

CREATE INDEX IF NOT EXISTS idx_football_competitions_country
    ON football_competitions (country);

CREATE INDEX IF NOT EXISTS idx_football_competitions_confederation
    ON football_competitions (confederation);

CREATE INDEX IF NOT EXISTS idx_football_competitions_tier
    ON football_competitions (tier);

CREATE INDEX IF NOT EXISTS idx_football_competitions_active
    ON football_competitions (active);

CREATE INDEX IF NOT EXISTS idx_football_competition_editions_competition
    ON football_competition_editions (competition_id);

CREATE INDEX IF NOT EXISTS idx_football_competition_editions_season
    ON football_competition_editions (season);

CREATE INDEX IF NOT EXISTS idx_football_competition_editions_dates
    ON football_competition_editions (start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_football_competition_editions_active
    ON football_competition_editions (active);

CREATE INDEX IF NOT EXISTS idx_football_team_competition_participation_team
    ON football_team_competition_participation (team_id);

CREATE INDEX IF NOT EXISTS idx_football_team_competition_participation_competition
    ON football_team_competition_participation (competition_id);

CREATE INDEX IF NOT EXISTS idx_football_team_competition_participation_edition
    ON football_team_competition_participation (edition_id);

CREATE INDEX IF NOT EXISTS idx_football_team_competition_participation_state
    ON football_team_competition_participation (participation_state);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_source_match
    ON football_match_targets (source, source_match_id);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_competition
    ON football_match_targets (competition_id);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_edition
    ON football_match_targets (edition_id);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_match_date
    ON football_match_targets (match_date);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_home_team
    ON football_match_targets (home_team_id);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_away_team
    ON football_match_targets (away_team_id);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_target_state
    ON football_match_targets (target_state);

CREATE INDEX IF NOT EXISTS idx_football_match_targets_raw_json_status
    ON football_match_targets (raw_json_status);

CREATE INDEX IF NOT EXISTS idx_football_match_target_teams_target
    ON football_match_target_teams (match_target_id);

CREATE INDEX IF NOT EXISTS idx_football_match_target_teams_team
    ON football_match_target_teams (team_id);

CREATE INDEX IF NOT EXISTS idx_football_match_target_teams_role
    ON football_match_target_teams (role);

CREATE INDEX IF NOT EXISTS idx_football_source_identities_entity
    ON football_source_identities (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_football_source_identities_source_entity_id
    ON football_source_identities (source, source_entity_id);

COMMENT ON TABLE football_teams IS 'Football team identity registry for club and national teams from FotMob.';
COMMENT ON COLUMN football_teams.source_team_id IS 'FotMob team id or source-specific team identity.';
COMMENT ON COLUMN football_teams.team_type IS 'Team type: club or national.';
COMMENT ON COLUMN football_teams.metadata IS 'Additional source identity metadata. No raw match payload.';

COMMENT ON TABLE football_competitions IS 'Football competition registry covering leagues, cups, continental club, and national team competitions.';
COMMENT ON COLUMN football_competitions.source_competition_id IS 'FotMob competition id or source-specific competition identity.';
COMMENT ON COLUMN football_competitions.competition_type IS 'Competition type enum used for calendar coverage and collector targeting.';
COMMENT ON COLUMN football_competitions.tier IS 'Collection coverage tier. Smaller values indicate higher priority.';

COMMENT ON TABLE football_competition_editions IS 'Competition season or tournament edition registry.';
COMMENT ON COLUMN football_competition_editions.season IS 'Season, calendar year, or tournament edition label.';
COMMENT ON COLUMN football_competition_editions.calendar_type IS 'Calendar shape such as season, calendar_year, or tournament_window.';

COMMENT ON TABLE football_team_competition_participation IS 'Team participation registry linking teams to competition editions for full-calendar reconstruction.';
COMMENT ON COLUMN football_team_competition_participation.participation_state IS 'Participation state: expected, confirmed, eliminated, completed, or unknown.';
COMMENT ON COLUMN football_team_competition_participation.qualification_source IS 'How this team entered the competition edition.';

COMMENT ON TABLE football_match_targets IS 'FotMob match detail collection targets. Stores target status only, not raw JSON.';
COMMENT ON COLUMN football_match_targets.source_match_id IS 'FotMob match id used to connect targets with fotmob_raw_match_payloads.match_id.';
COMMENT ON COLUMN football_match_targets.target_state IS 'Collection target state for raw JSON acquisition lifecycle.';
COMMENT ON COLUMN football_match_targets.raw_json_status IS 'Local summary of raw JSON storage state. Raw payload is stored outside this table.';

COMMENT ON TABLE football_match_target_teams IS 'Team-role join table for football match targets.';
COMMENT ON COLUMN football_match_target_teams.role IS 'Team role in a match target: home, away, or participant.';

COMMENT ON TABLE football_source_identities IS 'Source identity registry for teams, competitions, editions, and match targets.';
COMMENT ON COLUMN football_source_identities.entity_type IS 'Local entity type such as team, competition, edition, or match_target.';
COMMENT ON COLUMN football_source_identities.source_entity_id IS 'Source-specific entity id.';
