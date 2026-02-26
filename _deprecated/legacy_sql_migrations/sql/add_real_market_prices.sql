-- ===============================================================
-- 物理隔离重构 - Step 1: 数据库基准字段补完
-- 创建时间: 2024-12-23
-- 版本: v1.0
-- 描述: 在 matches 表中添加真实市场价格基准列
--
-- 目的：建立真实的市场价格基准，消除模拟定价带来的数据泄露
-- ===============================================================

BEGIN;

-- 添加 Bet365 真实市场价格列（首选基准）
ALTER TABLE matches
ADD COLUMN IF NOT EXISTS real_price_h REAL,              -- Bet365 主胜真实赔率
ADD COLUMN IF NOT EXISTS real_price_d REAL,              -- Bet365 平局真实赔率
ADD COLUMN IF NOT EXISTS real_price_a REAL;              -- Bet365 客胜真实赔率

-- 添加数据来源和采集时间字段
ALTER TABLE matches
ADD COLUMN IF NOT EXISTS real_price_source VARCHAR(50),  -- 价格来源（如: 'football-data.co.uk'）
ADD COLUMN IF NOT EXISTS real_price_collected_at TIMESTAMP WITH TIME ZONE,  -- 价格采集时间
ADD COLUMN IF NOT EXISTS real_price_quality VARCHAR(20) DEFAULT 'unknown';  -- 价格质量标识

-- 添加注释
COMMENT ON COLUMN matches.real_price_h IS 'Bet365 主胜真实赔率（基准价格，用于性能对账）';
COMMENT ON COLUMN matches.real_price_d IS 'Bet365 平局真实赔率（基准价格，用于性能对账）';
COMMENT ON COLUMN matches.real_price_a IS 'Bet365 客胜真实赔率（基准价格，用于性能对账）';
COMMENT ON COLUMN matches.real_price_source IS '价格数据来源标识';
COMMENT ON COLUMN matches.real_price_collected_at IS '市场价格采集时间';
COMMENT ON COLUMN matches.real_price_quality IS '价格质量标识: verified/estimated/unknown';

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_matches_real_prices
ON matches(real_price_h, real_price_d, real_price_a)
WHERE real_price_h IS NOT NULL;

-- 创建价格完整性检查视图
DROP VIEW IF EXISTS v_price_coverage;
CREATE VIEW v_price_coverage AS
SELECT
    DATE_TRUNC('day', match_time) AS match_date,
    COUNT(*) AS total_matches,
    COUNT(real_price_h) AS matches_with_home_odds,
    COUNT(real_price_d) AS matches_with_draw_odds,
    COUNT(real_price_a) AS matches_with_away_odds,
    COUNT(real_price_h) + COUNT(real_price_d) + COUNT(real_price_a) AS total_odds_count,
    ROUND(
        100.0 * COUNT(real_price_h) / NULLIF(COUNT(*), 0),
        2
    ) AS home_odds_coverage_pct,
    ROUND(
        100.0 * COUNT(real_price_d) / NULLIF(COUNT(*), 0),
        2
    ) AS draw_odds_coverage_pct,
    ROUND(
        100.0 * COUNT(real_price_a) / NULLIF(COUNT(*), 0),
        2
    ) AS away_odds_coverage_pct,
    ROUND(
        100.0 * COUNT(CASE WHEN real_price_h IS NOT NULL AND real_price_d IS NOT NULL AND real_price_a IS NOT NULL THEN 1 END) /
        NULLIF(COUNT(*), 0),
        2
    ) AS full_odds_coverage_pct
FROM matches
WHERE status = 'Finished'
GROUP BY DATE_TRUNC('day', match_time)
ORDER BY match_date DESC;

-- 添加约束确保价格数据合理性
-- 注意: PostgreSQL 不支持 ADD CONSTRAINT IF NOT EXISTS，使用 DO 块来检查并添加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_real_price_h_positive'
    ) THEN
        ALTER TABLE matches
        ADD CONSTRAINT chk_real_price_h_positive
        CHECK (real_price_h IS NULL OR real_price_h > 1.0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_real_price_d_positive'
    ) THEN
        ALTER TABLE matches
        ADD CONSTRAINT chk_real_price_d_positive
        CHECK (real_price_d IS NULL OR real_price_d > 1.0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_real_price_a_positive'
    ) THEN
        ALTER TABLE matches
        ADD CONSTRAINT chk_real_price_a_positive
        CHECK (real_price_a IS NULL OR real_price_a > 1.0);
    END IF;
END $$;

COMMIT;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '✅ Step 1 完成: 数据库基准字段补完';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '已添加列:';
    RAISE NOTICE '  - real_price_h: Bet365 主胜真实赔率';
    RAISE NOTICE '  - real_price_d: Bet365 平局真实赔率';
    RAISE NOTICE '  - real_price_a: Bet365 客胜真实赔率';
    RAISE NOTICE '  - real_price_source: 价格数据来源';
    RAISE NOTICE '  - real_price_collected_at: 价格采集时间';
    RAISE NOTICE '  - real_price_quality: 价格质量标识';
    RAISE NOTICE '';
    RAISE NOTICE '已创建视图: v_price_coverage (价格覆盖率监控)';
    RAISE NOTICE '已创建索引: idx_matches_real_prices';
    RAISE NOTICE '已添加约束: 价格数据合理性检查';
    RAISE NOTICE '';
    RAISE NOTICE '下一步: 执行 Step 2 - 外部市场数据映射';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '';
END $$;
