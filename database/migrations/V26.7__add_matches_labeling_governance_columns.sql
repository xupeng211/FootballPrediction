-- lifecycle: permanent
-- =============================================================================
-- V26.7 Database Migration: Add matches labeling governance columns
-- =============================================================================
-- 目标:
--   为 matches 表增加最小治理标签列，只做 additive nullable schema 变更。
--   不 backfill，不修改 pipeline_status，不写任何业务数据。
-- =============================================================================

ALTER TABLE matches
ADD COLUMN source_type VARCHAR(32),
ADD COLUMN evidence_level VARCHAR(24),
ADD COLUMN is_production_scope BOOLEAN,
ADD COLUMN is_reconciliation_eligible BOOLEAN,
ADD COLUMN is_training_eligible BOOLEAN,
ADD COLUMN pipeline_status_reason VARCHAR(64);

ALTER TABLE matches
ADD CONSTRAINT matches_source_type_valid
CHECK (
    source_type IS NULL
    OR source_type IN (
        'fotmob_live_fetch',
        'fotmob_html_hydration',
        'fotmob_pageprops',
        'manual_seed',
        'local_csv',
        'synthetic',
        'unknown'
    )
);

ALTER TABLE matches
ADD CONSTRAINT matches_evidence_level_valid
CHECK (
    evidence_level IS NULL
    OR evidence_level IN (
        'strong',
        'medium',
        'weak',
        'synthetic_invalid',
        'missing'
    )
);

ALTER TABLE matches
ADD CONSTRAINT matches_pipeline_status_reason_format
CHECK (
    pipeline_status_reason IS NULL
    OR pipeline_status_reason ~ '^[a-z][a-z0-9_]*$'
);

COMMENT ON COLUMN matches.source_type IS
'Match-level authoritative provenance class.';

COMMENT ON COLUMN matches.evidence_level IS
'Match-level evidence strength.';

COMMENT ON COLUMN matches.is_production_scope IS
'Whether match belongs to current production scope.';

COMMENT ON COLUMN matches.is_reconciliation_eligible IS
'Whether match may enter guarded reconciliation.';

COMMENT ON COLUMN matches.is_training_eligible IS
'Whether match may enter training datasets.';

COMMENT ON COLUMN matches.pipeline_status_reason IS
'Structured reason for current pipeline_status, especially pending, skipped, or failed.';
