-- lifecycle: permanent
-- V26.8 Historical odds staging persistence contract. DDL only; no migration has been executed by M3-D4B.
-- The nullable canonical_match_id deliberately has no FK: #1797 candidate IDs are not statically proven to be matches.match_id.

CREATE TABLE IF NOT EXISTS odds_historical_import_runs (
    id UUID PRIMARY KEY,
    run_key CHAR(64) NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type = 'historical_odds'),
    mode TEXT NOT NULL CHECK (mode IN ('dry_run', 'controlled_write')),
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'completed', 'failed', 'rolled_back', 'cancelled')),
    pipeline_version TEXT NOT NULL,
    pipeline_code_sha CHAR(40),
    manifest_hash CHAR(64),
    candidate_business_hash CHAR(64),
    expected_accepted_count INTEGER NOT NULL CHECK (expected_accepted_count >= 0),
    expected_quarantine_count INTEGER NOT NULL CHECK (expected_quarantine_count >= 0),
    actual_accepted_count INTEGER NOT NULL DEFAULT 0 CHECK (actual_accepted_count >= 0),
    actual_quarantine_count INTEGER NOT NULL DEFAULT 0 CHECK (actual_quarantine_count >= 0),
    duplicate_count INTEGER NOT NULL DEFAULT 0 CHECK (duplicate_count >= 0),
    failure_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT odds_historical_run_terminal_timestamp CHECK (
        NOT (completed_at IS NOT NULL AND failed_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS odds_historical_source_files (
    id UUID PRIMARY KEY,
    import_run_id UUID NOT NULL REFERENCES odds_historical_import_runs(id) ON DELETE RESTRICT,
    source_provider TEXT NOT NULL,
    logical_path TEXT,
    content_hash CHAR(64) NOT NULL,
    hash_algorithm TEXT NOT NULL CHECK (hash_algorithm = 'sha256'),
    manifest_hash CHAR(64),
    competition TEXT,
    season TEXT,
    row_count INTEGER CHECK (row_count IS NULL OR row_count >= 0),
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(provenance) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT odds_historical_source_file_run_hash_unique UNIQUE (import_run_id, content_hash)
);

CREATE TABLE IF NOT EXISTS odds_historical_staging_observations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id UUID NOT NULL REFERENCES odds_historical_import_runs(id) ON DELETE RESTRICT,
    source_file_id UUID NOT NULL REFERENCES odds_historical_source_files(id) ON DELETE RESTRICT,
    source_row_number INTEGER CHECK (source_row_number IS NULL OR source_row_number > 0),
    idempotency_key CHAR(64) NOT NULL UNIQUE,
    canonical_match_id TEXT,
    candidate_match_id TEXT,
    canonical_match_fk_status TEXT NOT NULL CHECK (canonical_match_fk_status IN ('unverified_database_fk', 'verified_database_fk')),
    historical_match_identity JSONB NOT NULL CHECK (jsonb_typeof(historical_match_identity) = 'object'),
    source_provider TEXT NOT NULL,
    source_match_id TEXT,
    competition TEXT,
    season TEXT,
    kickoff_at TIMESTAMPTZ,
    home_team TEXT,
    away_team TEXT,
    bookmaker TEXT NOT NULL,
    bookmaker_source_id TEXT,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    line NUMERIC(12, 6),
    decimal_odds NUMERIC(12, 6) NOT NULL CHECK (decimal_odds > 1),
    snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('opening', 'current', 'closing', 'unknown')),
    source_observed_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ,
    source_timezone TEXT,
    raw_sha256 CHAR(64) NOT NULL,
    raw_record_locator TEXT NOT NULL,
    adapter TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    extraction_method TEXT,
    provenance_status TEXT NOT NULL,
    source_quote_series TEXT,
    capture_time_status TEXT,
    kickoff_time_interpretation_evidence JSONB,
    match_link_evidence JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(match_link_evidence) = 'object'),
    audit_payload JSONB NOT NULL CHECK (jsonb_typeof(audit_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS odds_historical_quarantine (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id UUID NOT NULL REFERENCES odds_historical_import_runs(id) ON DELETE RESTRICT,
    source_file_id UUID NOT NULL REFERENCES odds_historical_source_files(id) ON DELETE RESTRICT,
    source_row_number INTEGER CHECK (source_row_number IS NULL OR source_row_number > 0),
    quarantine_key CHAR(64) NOT NULL UNIQUE,
    idempotency_key CHAR(64),
    reason_codes JSONB NOT NULL CHECK (jsonb_typeof(reason_codes) = 'array' AND jsonb_array_length(reason_codes) > 0),
    reason_detail JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(reason_detail) = 'object'),
    historical_match_identity JSONB NOT NULL CHECK (jsonb_typeof(historical_match_identity) = 'object'),
    source_payload JSONB NOT NULL CHECK (jsonb_typeof(source_payload) = 'object'),
    resolution_status TEXT NOT NULL DEFAULT 'open' CHECK (resolution_status IN ('open', 'resolved', 'rejected')),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_odds_historical_runs_status ON odds_historical_import_runs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_odds_historical_source_content_hash ON odds_historical_source_files (content_hash);
CREATE INDEX IF NOT EXISTS idx_odds_historical_observations_run ON odds_historical_staging_observations (import_run_id);
CREATE INDEX IF NOT EXISTS idx_odds_historical_observations_candidate ON odds_historical_staging_observations (candidate_match_id);
CREATE INDEX IF NOT EXISTS idx_odds_historical_quarantine_run ON odds_historical_quarantine (import_run_id);

COMMENT ON COLUMN odds_historical_staging_observations.canonical_match_id IS
'Nullable pending D4C database inventory: no FK until candidate identity is proven compatible with matches.match_id.';
COMMENT ON TABLE odds_historical_quarantine IS
'Separate from accepted observations; training readers must not use this table.';
