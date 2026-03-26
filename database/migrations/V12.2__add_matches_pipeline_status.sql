-- =============================================================================
-- V12.2 Database Migration: Add pipeline_status to matches
-- =============================================================================
-- 目标:
--   为 L1/L2 工业化流水线增加可观测的管道状态字段，避免复用比赛业务 status。
--
-- 状态定义:
--   pending / processing / harvested / failed / skipped
-- =============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(20) DEFAULT 'pending';

UPDATE matches m
SET pipeline_status = CASE
    WHEN r.match_id IS NOT NULL THEN 'harvested'
    ELSE COALESCE(m.pipeline_status, 'pending')
END,
updated_at = NOW()
FROM (
    SELECT match_id
    FROM raw_match_data
) r
WHERE m.match_id = r.match_id
   OR m.pipeline_status IS NULL;

ALTER TABLE matches
ALTER COLUMN pipeline_status SET DEFAULT 'pending';

ALTER TABLE matches
DROP CONSTRAINT IF EXISTS matches_pipeline_status_valid;

ALTER TABLE matches
ADD CONSTRAINT matches_pipeline_status_valid
CHECK (pipeline_status IN ('pending', 'processing', 'harvested', 'failed', 'skipped'));

CREATE INDEX IF NOT EXISTS idx_matches_pipeline_status
ON matches(pipeline_status);

COMMENT ON COLUMN matches.pipeline_status IS
'L1/L2 工业化流水线状态: pending, processing, harvested, failed, skipped';
