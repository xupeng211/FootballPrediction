-- =============================================================================
-- V12.3 Database Migration: Expand pipeline_status for Recon
-- =============================================================================
-- 目标:
--   为 L2 Recon Matrix 增加合法状态，完成 harvested -> RECON_LINKED /
--   RECON_MISMATCH 的闭环推进。
--
-- 新状态:
--   RECON_LINKED / RECON_MISMATCH
-- =============================================================================

ALTER TABLE matches
DROP CONSTRAINT IF EXISTS matches_pipeline_status_valid;

ALTER TABLE matches
ADD CONSTRAINT matches_pipeline_status_valid
CHECK (
  pipeline_status IN (
    'pending',
    'processing',
    'harvested',
    'failed',
    'skipped',
    'RECON_LINKED',
    'RECON_MISMATCH'
  )
);

COMMENT ON COLUMN matches.pipeline_status IS
'L1/L2 工业化流水线状态: pending, processing, harvested, failed, skipped, RECON_LINKED, RECON_MISMATCH';
