-- ===============================================================
-- FootballPrediction L3 赔率数据架构扩展
-- 功能: 为 raw_match_data 表添加 L3 赔率原始数据存储
-- 创建时间: 2024-12-20
-- 版本: v3.1.0
-- ===============================================================

-- 开始事务
BEGIN;

-- ===============================================================
-- 1. 为 raw_match_data 表添加 L3 赔率数据字段
-- ===============================================================

-- 添加 L3 赔率原始数据字段
ALTER TABLE raw_match_data
ADD COLUMN IF NOT EXISTS raw_odds_data JSONB,
ADD COLUMN IF NOT EXISTS odds_data_source VARCHAR(50) DEFAULT 'fotmob_matchodds',
ADD COLUMN IF NOT EXISTS odds_data_version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS odds_collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS odds_parse_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS odds_parse_error TEXT;

-- 添加约束 (PostgreSQL 不支持 IF NOT EXISTS for constraints)
DO $$
BEGIN
    -- 检查约束是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'raw_match_data_odds_parse_status_check'
        AND conrelid = 'raw_match_data'::regclass
    ) THEN
        ALTER TABLE raw_match_data
        ADD CONSTRAINT raw_match_data_odds_parse_status_check
        CHECK (odds_parse_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped'));
    END IF;
END $$;

-- ===============================================================
-- 2. 创建 L3 赔率数据索引
-- ===============================================================

-- 赔率数据搜索优化索引
CREATE INDEX IF NOT EXISTS idx_raw_match_data_raw_odds_gin ON raw_match_data USING GIN(raw_odds_data);

-- 赔率数据状态索引
CREATE INDEX IF NOT EXISTS idx_raw_match_data_odds_parse_status ON raw_match_data(odds_parse_status)
WHERE odds_parse_status != 'completed';

-- 赔率数据采集时间索引
CREATE INDEX IF NOT EXISTS idx_raw_match_data_odds_collected_at ON raw_match_data(odds_collected_at DESC);

-- 组合索引 - 用于查找已采集L2但未采集L3的比赛
CREATE INDEX IF NOT EXISTS idx_raw_match_data_l2_no_l3 ON raw_match_data(external_id, raw_match_data)
WHERE raw_match_data IS NOT NULL AND raw_odds_data IS NULL;

-- ===============================================================
-- 3. 创建 L3 赔率数据监控视图
-- ===============================================================

-- L3 赔率数据采集状态视图
DROP VIEW IF EXISTS v_l3_odds_collection_status;
CREATE VIEW v_l3_odds_collection_status AS
SELECT
    m.external_id,
    m.home_team || ' vs ' || m.away_team AS match_name,
    m.match_time,
    m.status AS match_status,
    rmd.raw_match_data IS NOT NULL AS has_l2_data,
    rmd.raw_odds_data IS NOT NULL AS has_l3_odds_data,
    rmd.odds_parse_status,
    rmd.odds_data_source,
    rmd.odds_collected_at,
    rmd.updated_at AS odds_updated_at,
    CASE
        WHEN rmd.raw_match_data IS NOT NULL AND rmd.raw_odds_data IS NOT NULL THEN 'COMPLETE'
        WHEN rmd.raw_match_data IS NOT NULL AND rmd.raw_odds_data IS NULL THEN 'MISSING_L3'
        WHEN rmd.raw_match_data IS NULL AND rmd.raw_odds_data IS NOT NULL THEN 'MISSING_L2'
        ELSE 'EMPTY'
    END AS collection_status,
    -- 赔率数据完整性检查
    CASE
        WHEN rmd.raw_odds_data IS NOT NULL THEN
            CASE
                WHEN rmd.raw_odds_data->'data' IS NOT NULL THEN 'VALID'
                WHEN jsonb_typeof(rmd.raw_odds_data) = 'object' THEN 'PARSABLE'
                ELSE 'INVALID'
            END
        ELSE 'MISSING'
    END AS odds_data_quality
FROM matches m
LEFT JOIN raw_match_data rmd ON m.external_id = rmd.external_id
ORDER BY m.match_time DESC;

-- L3 赔率数据统计视图
DROP VIEW IF EXISTS v_l3_odds_collection_stats;
CREATE VIEW v_l3_odds_collection_stats AS
SELECT
    DATE_TRUNC('day', m.match_time) AS collection_date,
    COUNT(*) AS total_matches,
    COUNT(CASE WHEN rmd.raw_match_data IS NOT NULL THEN 1 END) AS l2_collected,
    COUNT(CASE WHEN rmd.raw_odds_data IS NOT NULL THEN 1 END) AS l3_odds_collected,
    COUNT(CASE WHEN rmd.raw_odds_data IS NOT NULL AND rmd.odds_parse_status = 'completed' THEN 1 END) AS l3_parsed,
    ROUND(
        COUNT(CASE WHEN rmd.raw_odds_data IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS l3_odds_collection_rate,
    ROUND(
        COUNT(CASE WHEN rmd.raw_odds_data IS NOT NULL AND rmd.odds_parse_status = 'completed' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS l3_odds_parse_rate
FROM matches m
LEFT JOIN raw_match_data rmd ON m.external_id = rmd.external_id
WHERE m.match_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', m.match_time)
ORDER BY collection_date DESC;

-- ===============================================================
-- 4. 数据库统计信息更新
-- ===============================================================

-- 更新统计信息以优化查询计划
ANALYZE raw_match_data;
ANALYZE matches;

-- ===============================================================
-- 5. 完成提示
-- ===============================================================

-- 提交事务
COMMIT;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE 'FootballPrediction L3 赔率数据架构扩展完成';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '✅ 已添加 raw_odds_data (JSONB) 字段到 raw_match_data 表';
    RAISE NOTICE '✅ 已添加 odds_parse_status 等管理字段';
    RAISE NOTICE '✅ 已创建 L3 赔率数据索引 (GIN, B-Tree)';
    RAISE NOTICE '✅ 已创建 v_l3_odds_collection_status 监控视图';
    RAISE NOTICE '✅ 已创建 v_l3_odds_collection_stats 统计视图';
    RAISE NOTICE '✅ 已更新表统计信息';
    RAISE NOTICE '';
    RAISE NOTICE '📊 监控查询示例:';
    RAISE NOTICE '   SELECT * FROM v_l3_odds_collection_status LIMIT 10;';
    RAISE NOTICE '   SELECT * FROM v_l3_odds_collection_stats;';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 L3 赔率数据架构已就绪，可以开始赔率数据采集!';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '';
END $$;