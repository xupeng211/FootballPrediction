-- ===============================================================
-- FootballPrediction 赔率数据独立存储架构
-- 功能: 创建独立的 match_odds 表存储赔率时序数据
-- 创建时间: 2025-12-29
-- 版本: v1.0
-- ===============================================================

BEGIN;

-- ===============================================================
-- 1. 创建 match_odds 表
-- ===============================================================
CREATE TABLE IF NOT EXISTS match_odds (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 关联字段
    match_id VARCHAR(50) NOT NULL,                       -- 关联 matches.match_id
    external_id VARCHAR(100),                            -- 外部比赛ID (冗余字段，便于查询)

    -- 赔率数据字段
    provider VARCHAR(50) NOT NULL,                       -- 数据源 (bet365, william_hill, etc.)
    home_win_odds NUMERIC(10, 4),                        -- 主胜赔率
    draw_odds NUMERIC(10, 4),                            -- 平局赔率
    away_win_odds NUMERIC(10, 4),                        -- 客胜赔率

    -- 扩展赔率字段 (可选)
    asian_handicap_home NUMERIC(5, 2),                   -- 亚盘主队让球
    asian_handicap_home_odds NUMERIC(10, 4),             -- 亚盘主队赔率
    over_under_line NUMERIC(5, 2),                       -- 大小球盘口
    over_odds NUMERIC(10, 4),                            -- 大球赔率
    under_odds NUMERIC(10, 4),                           -- 小球赔率

    -- 市场信息
    market_type VARCHAR(20) DEFAULT '1X2',               -- 市场类型 (1X2, AH, OU)
    is_opening BOOLEAN DEFAULT FALSE,                    -- 是否为初盘赔率
    is_closing BOOLEAN DEFAULT FALSE,                    -- 是否为终盘赔率

    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,         -- 赔率记录时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 约束定义
    CONSTRAINT match_odds_provider_check CHECK (
        provider IN ('bet365', 'william_hill', 'ladbrokes', 'pinnacle',
                     'betfair', 'unibet', 'bwin', 'other')
    ),
    CONSTRAINT match_odds_market_type_check CHECK (
        market_type IN ('1X2', 'AH', 'OU', 'ALL')
    ),
    CONSTRAINT match_odds_odds_positive CHECK (
        (home_win_odds IS NULL OR home_win_odds > 0) AND
        (draw_odds IS NULL OR draw_odds > 0) AND
        (away_win_odds IS NULL OR away_win_odds > 0)
    )
);

-- ===============================================================
-- 2. 外键约束
-- ===============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_match_odds_matches'
        AND conrelid = 'match_odds'::regclass
    ) THEN
        ALTER TABLE match_odds
        ADD CONSTRAINT fk_match_odds_matches
        FOREIGN KEY (match_id) REFERENCES matches(match_id)
        ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;
END $$;

-- ===============================================================
-- 3. 索引优化
-- ===============================================================

-- 复合索引: 按 match_id 和 timestamp 查询 (主要查询模式)
CREATE INDEX IF NOT EXISTS idx_match_odds_match_timestamp
ON match_odds(match_id, timestamp DESC);

-- 索引: 按 external_id 查询
CREATE INDEX IF NOT EXISTS idx_match_odds_external_id
ON match_odds(external_id);

-- 索引: 按 provider 筛选
CREATE INDEX IF NOT EXISTS idx_match_odds_provider
ON match_odds(provider);

-- 索引: 初盘/终盘标识
CREATE INDEX IF NOT EXISTS idx_match_odds_is_opening
ON match_odds(is_opening) WHERE is_opening = TRUE;

CREATE INDEX IF NOT EXISTS idx_match_odds_is_closing
ON match_odds(is_closing) WHERE is_closing = TRUE;

-- 部分索引: 仅索引有效赔率数据
CREATE INDEX IF NOT EXISTS idx_match_odds_valid_1x2
ON match_odds(match_id, timestamp DESC)
WHERE home_win_odds IS NOT NULL
  AND draw_odds IS NOT NULL
  AND away_win_odds IS NOT NULL;

-- ===============================================================
-- 4. 监控视图
-- ===============================================================

-- 赔率数据概览视图
DROP VIEW IF EXISTS v_match_odds_overview;
CREATE VIEW v_match_odds_overview AS
SELECT
    m.match_id,
    m.external_id,
    m.home_team || ' vs ' || m.away_team AS match_name,
    m.match_date AS match_time,
    m.status,
    -- 赔率数据源数量
    COUNT(DISTINCT mo.provider) AS provider_count,
    -- 初盘赔率
    MAX(mo.home_win_odds) FILTER (WHERE mo.is_opening = TRUE) AS opening_home_odds,
    MAX(mo.draw_odds) FILTER (WHERE mo.is_opening = TRUE) AS opening_draw_odds,
    MAX(mo.away_win_odds) FILTER (WHERE mo.is_opening = TRUE) AS opening_away_odds,
    -- 终盘赔率
    MAX(mo.home_win_odds) FILTER (WHERE mo.is_closing = TRUE) AS closing_home_odds,
    MAX(mo.draw_odds) FILTER (WHERE mo.is_closing = TRUE) AS closing_draw_odds,
    MAX(mo.away_win_odds) FILTER (WHERE mo.is_closing = TRUE) AS closing_away_odds,
    -- 最新赔率时间
    MAX(mo.timestamp) AS latest_odds_timestamp,
    CASE
        WHEN COUNT(DISTINCT mo.provider) > 0 THEN 'YES'
        ELSE 'NO'
    END AS has_odds_data
FROM matches m
LEFT JOIN match_odds mo ON m.match_id = mo.match_id
GROUP BY m.match_id, m.external_id, m.home_team, m.away_team, m.match_date, m.status
ORDER BY m.match_date DESC;

-- 赔率时序数据视图 (用于分析赔率变动)
DROP VIEW IF EXISTS v_match_odds_timeseries;
CREATE VIEW v_match_odds_timeseries AS
SELECT
    m.match_id,
    m.external_id,
    m.home_team || ' vs ' || m.away_team AS match_name,
    mo.provider,
    mo.market_type,
    mo.home_win_odds,
    mo.draw_odds,
    mo.away_win_odds,
    mo.timestamp,
    -- 计算隐含概率
    CASE
        WHEN mo.home_win_odds > 0 THEN ROUND(100.0 / mo.home_win_odds, 2)
        ELSE NULL
    END AS home_implied_prob,
    CASE
        WHEN mo.draw_odds > 0 THEN ROUND(100.0 / mo.draw_odds, 2)
        ELSE NULL
    END AS draw_implied_prob,
    CASE
        WHEN mo.away_win_odds > 0 THEN ROUND(100.0 / mo.away_win_odds, 2)
        ELSE NULL
    END AS away_implied_prob
FROM matches m
INNER JOIN match_odds mo ON m.match_id = mo.match_id
ORDER BY m.match_date DESC, mo.timestamp ASC;

-- ===============================================================
-- 5. 统计信息更新
-- ===============================================================
ANALYZE match_odds;

-- ===============================================================
-- 6. 完成提示
-- ===============================================================
COMMIT;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE 'FootballPrediction 赔率数据独立存储架构完成';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '✅ 已创建 match_odds 表';
    RAISE NOTICE '✅ 已添加外键约束关联 matches 表';
    RAISE NOTICE '✅ 已创建复合索引 (match_id, timestamp)';
    RAISE NOTICE '✅ 已创建 v_match_odds_overview 视图';
    RAISE NOTICE '✅ 已创建 v_match_odds_timeseries 视图';
    RAISE NOTICE '';
    RAISE NOTICE '📊 监控查询示例:';
    RAISE NOTICE '   SELECT * FROM v_match_odds_overview LIMIT 10;';
    RAISE NOTICE '   SELECT * FROM v_match_odds_timeseries WHERE external_id = ''xxx'';';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 赔率数据架构已就绪!';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '';
END $$;
