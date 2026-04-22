-- ============================================================================
-- V12.7 为 matches 增加战术维度字段
-- ============================================================================
-- 目标:
--   为 football-data.co.uk 等离线赔率源补充高价值比赛元数据，
--   为后续特征工程提供角球、牌数、裁判等战术维度。
-- ============================================================================

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS home_corners INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS away_corners INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS home_yellow_cards INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS away_yellow_cards INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS home_red_cards INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS away_red_cards INT;

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS referee VARCHAR(100);

COMMENT ON COLUMN matches.home_corners IS '主队角球数';
COMMENT ON COLUMN matches.away_corners IS '客队角球数';
COMMENT ON COLUMN matches.home_yellow_cards IS '主队黄牌数';
COMMENT ON COLUMN matches.away_yellow_cards IS '客队黄牌数';
COMMENT ON COLUMN matches.home_red_cards IS '主队红牌数';
COMMENT ON COLUMN matches.away_red_cards IS '客队红牌数';
COMMENT ON COLUMN matches.referee IS '裁判姓名';
