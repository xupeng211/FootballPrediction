-- ============================================================================
-- V12.6 允许 raw_match_data 使用纯数字 FotMob match_id
-- ============================================================================
-- 背景:
--   Titan 当前以 FotMob 官方 matchId 作为唯一真相源。
--   历史 V6.6 约束仅允许 legacy 三段式 match_id，阻断了纯数字样板房缝合。
-- 目标:
--   放宽 raw_match_data.match_id 约束，兼容:
--   1. legacy: {league_id}_{season_tag}_{external_id}
--   2. fotmob: {external_id}
-- ============================================================================

ALTER TABLE raw_match_data
DROP CONSTRAINT IF EXISTS match_id_format;

ALTER TABLE raw_match_data
ADD CONSTRAINT match_id_format
CHECK (
  match_id ~ '^\d+_\d{8}_\d+$'
  OR match_id ~ '^\d+$'
);

COMMENT ON CONSTRAINT match_id_format ON raw_match_data IS
  '兼容 legacy 三段式与纯数字 FotMob 官方 match_id';
