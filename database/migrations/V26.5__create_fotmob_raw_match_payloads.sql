-- V26.5: Create fotmob_raw_match_payloads table for ADG60 raw JSON storage.
-- Stores raw __NEXT_DATA__ and pageProps JSON from FotMob match detail pages.
-- No feature parsing. No raw_match_data insert. No predictions write.

CREATE TABLE IF NOT EXISTS fotmob_raw_match_payloads (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'fotmob',
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    match_id TEXT NOT NULL,
    target_index INTEGER,
    expected_home TEXT,
    expected_away TEXT,
    expected_date DATE,
    route_hash TEXT,
    source_url TEXT,
    raw_payload_file_path TEXT NOT NULL,
    raw_payload_sha256 TEXT NOT NULL,
    raw_payload_byte_size INTEGER NOT NULL,
    raw_payload_content_type TEXT,
    captured_at TIMESTAMPTZ,
    next_data_found BOOLEAN NOT NULL DEFAULT FALSE,
    next_data_sha256 TEXT,
    next_data_json JSONB NOT NULL,
    page_props_found BOOLEAN NOT NULL DEFAULT FALSE,
    page_props_sha256 TEXT,
    page_props_json JSONB,
    json_storage_version TEXT NOT NULL DEFAULT 'adg60_raw_json_v1',
    parser_version TEXT,
    ingestion_run_id TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active_snapshot BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    CONSTRAINT uq_fotmob_source_match_sha256 UNIQUE (source, match_id, raw_payload_sha256)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fotmob_raw_payloads_source_match
    ON fotmob_raw_match_payloads (source, match_id);

CREATE INDEX IF NOT EXISTS idx_fotmob_raw_payloads_comp_season
    ON fotmob_raw_match_payloads (competition, season);

CREATE INDEX IF NOT EXISTS idx_fotmob_raw_payloads_run_id
    ON fotmob_raw_match_payloads (ingestion_run_id);

CREATE INDEX IF NOT EXISTS idx_fotmob_raw_payloads_next_data
    ON fotmob_raw_match_payloads USING GIN (next_data_json);

CREATE INDEX IF NOT EXISTS idx_fotmob_raw_payloads_page_props
    ON fotmob_raw_match_payloads USING GIN (page_props_json);

-- Comments
COMMENT ON TABLE fotmob_raw_match_payloads IS 'FotMob ADG60 raw match detail payloads with __NEXT_DATA__ and pageProps JSON. No feature parsing.';
COMMENT ON COLUMN fotmob_raw_match_payloads.next_data_json IS 'Complete __NEXT_DATA__ JSON from FotMob match detail page. Raw, unparsed.';
COMMENT ON COLUMN fotmob_raw_match_payloads.page_props_json IS 'Complete props.pageProps JSON from FotMob __NEXT_DATA__. Raw, unparsed.';
COMMENT ON COLUMN fotmob_raw_match_payloads.ingestion_run_id IS 'Batch ingestion run identifier for idempotency tracking.';
COMMENT ON COLUMN fotmob_raw_match_payloads.is_active_snapshot IS 'Marks the latest snapshot for a given match. Set to false on re-ingestion.';
COMMENT ON COLUMN fotmob_raw_match_payloads.json_storage_version IS 'Schema version for future raw JSON format migrations.';
