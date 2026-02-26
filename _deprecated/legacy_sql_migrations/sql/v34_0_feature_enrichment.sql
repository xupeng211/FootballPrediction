-- ============================================================================
-- V34.0 Feature Enrichment - 特征增强引擎
-- ============================================================================
-- Purpose: 添加新特征字段支持高级分析
--
-- 核心功能：
-- 1. payout_ratio: 博彩公司返还率（识别冷门诱导盘）
-- 2. movement_velocity: 赛前 2 小时变盘速度（捕捉主力资金动向）
-- 3. review_needed: 队名别名审核标记（防范冲突）
--
-- Author: 高级数据治理专家 & 算法工程师
-- Date: 2026-01-12
-- Version: V34.0 (Feature Enrichment)
-- ============================================================================

-- 1. 添加新特征字段到 match_features 表
ALTER TABLE match_features
    ADD COLUMN IF NOT EXISTS payout_ratio REAL,
    ADD COLUMN IF NOT EXISTS movement_velocity REAL DEFAULT 0.0;

-- 添加注释
COMMENT ON COLUMN match_features.payout_ratio IS 'V34.0: 博彩公司返还率 (0-1)。正常范围: 0.90-0.98。高值 (>0.95) 可能是冷门诱导盘';
COMMENT ON COLUMN match_features.movement_velocity IS 'V34.0: 赛前 2 小时变盘速度 (次/小时)。高值 (>20) 表示主力资金活跃';

-- 创建索引（用于查询高返还率比赛）
CREATE INDEX IF NOT EXISTS idx_match_features_payout_ratio
    ON match_features(payout_ratio)
    WHERE payout_ratio IS NOT NULL;

-- 创建索引（用于查询高变盘速度比赛）
CREATE INDEX IF NOT EXISTS idx_match_features_movement_velocity
    ON match_features(movement_velocity)
    WHERE movement_velocity > 0;

-- ============================================================================
-- 2. 添加审核标记字段到 team_aliases 表
-- ============================================================================

ALTER TABLE team_aliases
    ADD COLUMN IF NOT EXISTS review_needed BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100);

-- 添加注释
COMMENT ON COLUMN team_aliases.review_needed IS 'V34.0: 是否需要人工审核。70%-85% 匹配分数的别名标记为 TRUE';
COMMENT ON COLUMN team_aliases.reviewed_at IS 'V34.0: 审核完成时间';
COMMENT ON COLUMN team_aliases.reviewed_by IS 'V34.0: 审核人标识';

-- 创建索引（查询待审核别名）
CREATE INDEX IF NOT EXISTS idx_team_aliases_review_needed
    ON team_aliases(review_needed)
    WHERE review_needed = TRUE;

-- ============================================================================
-- 3. 创建辅助视图
-- ============================================================================

-- 高返还率比赛视图（潜在冷门诱导盘）
CREATE OR REPLACE VIEW v_high_payout_matches AS
SELECT
    mf.match_id,
    m.league_name,
    m.home_team,
    m.away_team,
    mf.payout_ratio,
    mf.closing_home,
    mf.closing_draw,
    mf.closing_away,
    m.match_date
FROM match_features mf
JOIN matches m ON mf.match_id = m.match_id
WHERE mf.payout_ratio > 0.95
  AND m.match_date > NOW() - INTERVAL '30 days'
ORDER BY mf.payout_ratio DESC;

COMMENT ON VIEW v_high_payout_matches IS 'V34.0: 高返还率比赛视图（潜在冷门诱导盘）';

-- 高变盘速度比赛视图（主力资金活跃）
CREATE OR REPLACE VIEW v_high_velocity_matches AS
SELECT
    mf.match_id,
    m.league_name,
    m.home_team,
    m.away_team,
    mf.movement_velocity,
    m.match_date
FROM match_features mf
JOIN matches m ON mf.match_id = m.match_id
WHERE mf.movement_velocity > 20
  AND m.match_date > NOW() - INTERVAL '30 days'
ORDER BY mf.movement_velocity DESC;

COMMENT ON VIEW v_high_velocity_matches IS 'V34.0: 高变盘速度比赛视图（主力资金活跃）';

-- 待审核队名别名视图
CREATE OR REPLACE VIEW v_team_aliases_review_queue AS
SELECT
    alias_slug,
    canonical_name,
    league_name,
    confidence,
    alias_type,
    usage_count,
    created_at
FROM team_aliases
WHERE review_needed = TRUE
ORDER BY confidence DESC, usage_count DESC;

COMMENT ON VIEW v_team_aliases_review_queue IS 'V34.0: 待审核队名别名视图';

-- ============================================================================
-- 4. 数据迁移（现有数据默认值）
-- ============================================================================

-- 为现有 match_features 记录计算 payout_ratio
UPDATE match_features
SET payout_ratio = CASE
    WHEN closing_home > 0 AND closing_draw > 0 AND closing_away > 0
    THEN 1.0 / (1.0/closing_home + 1.0/closing_draw + 1.0/closing_away)
    ELSE NULL
END
WHERE payout_ratio IS NULL
  AND closing_home IS NOT NULL;

-- 为现有 match_features 记录设置默认 movement_velocity
UPDATE match_features
SET movement_velocity = 0.0
WHERE movement_velocity IS NULL;

-- ============================================================================
-- 5. 统计信息
-- ============================================================================

-- 显示迁移结果
DO $$
DECLARE
    total_features INT;
    with_payout INT;
    with_velocity INT;
    high_payout INT;
    high_velocity INT;
BEGIN
    SELECT COUNT(*) INTO total_features FROM match_features;
    SELECT COUNT(*) INTO with_payout FROM match_features WHERE payout_ratio IS NOT NULL;
    SELECT COUNT(*) INTO with_velocity FROM match_features WHERE movement_velocity > 0;
    SELECT COUNT(*) INTO high_payout FROM match_features WHERE payout_ratio > 0.95;
    SELECT COUNT(*) INTO high_velocity FROM match_features WHERE movement_velocity > 20;

    RAISE NOTICE '=== V34.0 Feature Enrichment 迁移完成 ===';
    RAISE NOTICE '总特征记录数: %', total_features;
    RAISE NOTICE '有返还率: % (%.1f%%)', with_payout, 100.0 * with_payout / NULLIF(total_features, 0);
    RAISE NOTICE '有变盘速度: % (%.1f%%)', with_velocity, 100.0 * with_velocity / NULLIF(total_features, 0);
    RAISE NOTICE '高返还率 (>0.95): %', high_payout;
    RAISE NOTICE '高变盘速度 (>20): %', high_velocity;
END $$;
