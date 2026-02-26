-- ============================================================================
-- V37.5 性能索引预热 - 加速生产线查询
-- ============================================================================
-- 功能: 为高频查询添加复合索引，确保毫秒级响应
--
-- 索引设计:
-- 1. idx_matches_date_status - 加速"最近 1 小时未处理比赛"查询
-- 2. idx_matches_league_date - 加速按联赛筛选比赛
-- 3. idx_matches_mapping_url - 加速 URL 查询
-- 4. idx_match_features_payout - 加速特征完整性检查
--
-- Author: 首席 SRE & 性能保障官
-- Version: V37.5
-- Date: 2026-01-12
-- ============================================================================

-- 1. 核心索引: match_date + l3_extraction_status
-- 用于: 启动自检、生产线指标 A→B 查询
CREATE INDEX IF NOT EXISTS idx_matches_date_status
ON matches(match_date DESC, l3_extraction_status)
WHERE l3_extraction_status IN ('pending', 'in_progress');

-- 2. 联赛索引: league_name + match_date
-- 用于: 按联赛筛选、批量处理
CREATE INDEX IF NOT EXISTS idx_matches_league_date
ON matches(league_name, match_date DESC);

-- 3. URL 映射索引: oddsportal_url
-- 用于: Layer B → C 哈希狩猎
CREATE INDEX IF NOT EXISTS idx_matches_mapping_url
ON matches_mapping(oddsportal_url)
WHERE oddsportal_url IS NOT NULL;

-- 4. 特征完整性索引: payout_ratio
-- 用于: C→D 成功率监控
CREATE INDEX IF NOT EXISTS idx_match_features_payout
ON match_features(payout_ratio)
WHERE payout_ratio IS NOT NULL;

-- 5. l3_odds_data 索引 (V37.4 Layer D 触发器优化)
-- 用于: 查找有赔率数据的比赛
CREATE INDEX IF NOT EXISTS idx_matches_odds_data
ON matches(match_id)
WHERE l3_odds_data IS NOT NULL;

-- 验证索引创建
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('matches', 'matches_mapping', 'match_features')
  AND indexname LIKE 'idx_%'
ORDER BY indexname;

-- 输出确认信息
DO $$
BEGIN
    RAISE NOTICE '======================================================================';
    RAISE NOTICE 'V37.5 性能索引预热完成';
    RAISE NOTICE '======================================================================';
    RAISE NOTICE '已创建 5 个复合索引:';
    RAISE NOTICE '  1. idx_matches_date_status - match_date + l3_extraction_status';
    RAISE NOTICE '  2. idx_matches_league_date - league_name + match_date';
    RAISE NOTICE '  3. idx_matches_mapping_url - oddsportal_url';
    RAISE NOTICE '  4. idx_match_features_payout - payout_ratio';
    RAISE NOTICE '  5. idx_matches_odds_data - l3_odds_data';
    RAISE NOTICE '======================================================================';
END $$;
