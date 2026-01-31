-- ===============================================================
-- FootballPrediction L1/L2 数据采集架构 - 基础表结构
-- 创建时间: 2024-12-19
-- 版本: v1.0
-- 环境要求: PostgreSQL 15+
-- 描述: 足球比赛数据采集的L1索引底座和L2原始数据存储
-- ===============================================================

-- 开始事务
BEGIN;

-- ===============================================================
-- 1. L1 表：比赛索引底座 (matches)
-- 功能: 存储比赛基础信息，作为L2采集的索引表
-- ===============================================================
CREATE TABLE IF NOT EXISTS matches (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 业务核心字段
    external_id VARCHAR(50) NOT NULL,                    -- 外部比赛ID (FotMob ID)
    league_name VARCHAR(100) NOT NULL,                   -- 联赛名称 (如: Premier League)
    season VARCHAR(20) NOT NULL,                         -- 赛季 (如: 2024/25)
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,        -- 比赛时间 (UTC)
    status VARCHAR(50) NOT NULL DEFAULT 'Fixture',       -- 比赛状态
    home_team VARCHAR(100) NOT NULL,                     -- 主队名称
    away_team VARCHAR(100) NOT NULL,                     -- 客队名称

    -- L2采集状态管理
    collection_status VARCHAR(20) DEFAULT 'pending',     -- L2采集状态

    -- 扩展字段 (为将来功能预留)
    league_id VARCHAR(50),                               -- 联赛ID
    home_team_id VARCHAR(50),                            -- 主队ID
    away_team_id VARCHAR(50),                            -- 客队ID
    venue_name VARCHAR(200),                             -- 场地名称
    result_score VARCHAR(20),                            -- 最终比分
    round_info VARCHAR(50),                              -- 轮次信息

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    l1_collected_at TIMESTAMP WITH TIME ZONE,            -- L1采集时间
    l2_collected_at TIMESTAMP WITH TIME ZONE,            -- L2采集时间

    -- 约束定义
    CONSTRAINT matches_external_id_unique UNIQUE(external_id),
    CONSTRAINT matches_status_check CHECK (
        status IN ('Fixture', 'Live', 'Finished', 'Postponed', 'Cancelled', 'Abandoned')
    ),
    CONSTRAINT matches_collection_status_check CHECK (
        collection_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    )
);

-- ===============================================================
-- 2. L2 表：原始比赛详情数据 (raw_match_data)
-- 功能: 存储从API获取的原始JSON数据
-- ===============================================================
CREATE TABLE IF NOT EXISTS raw_match_data (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 关联字段
    external_id VARCHAR(50) NOT NULL,                    -- 外部比赛ID (关联matches.external_id)

    -- 数据字段
    raw_data JSONB,                                      -- 原始JSON数据 (FotMob API响应)
    raw_match_data JSONB,                                -- 原始比赛详情数据 (备用字段)
    source VARCHAR(50) DEFAULT 'fotmob',                -- 数据源标识
    data_version INTEGER DEFAULT 1,                      -- 数据版本号 (用于版本管理)

    -- 高阶解析状态管理
    parsed BOOLEAN DEFAULT FALSE,                        -- 是否已被高阶解析器处理
    parse_status VARCHAR(20) DEFAULT 'pending',          -- 解析状态
    parse_error TEXT,                                    -- 解析错误信息

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- 数据采集时间

    -- 约束定义
    CONSTRAINT raw_match_data_external_id_unique UNIQUE(external_id),
    CONSTRAINT raw_match_data_parse_status_check CHECK (
        parse_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    )
);

-- ===============================================================
-- 3. 特征表：85个预测因子 (match_features_training)
-- 功能: 存储从L2数据提取的所有机器学习特征
-- ===============================================================
CREATE TABLE IF NOT EXISTS match_features_training (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 关联字段
    external_id VARCHAR(50) NOT NULL,                    -- 外部比赛ID

    -- 比赛基础信息
    home_team VARCHAR(100),                              -- 主队名称
    away_team VARCHAR(100),                              -- 客队名称
    match_time TIMESTAMP WITH TIME ZONE,                 -- 比赛时间

    -- A. 基础特征 (20个)
    final_score VARCHAR(20),                             -- 最终比分
    home_goals INTEGER,                                  -- 主队进球数
    away_goals INTEGER,                                  -- 客队进球数
    home_possession REAL,                                -- 主队控球率
    away_possession REAL,                                -- 客队控球率
    home_shots_on_target INTEGER,                        -- 主队射正数
    away_shots_on_target INTEGER,                        -- 客队射正数
    home_corners INTEGER,                                -- 主队角球数
    away_corners INTEGER,                                -- 客队角球数
    home_total_shots INTEGER,                            -- 主队总射门数
    away_total_shots INTEGER,                            -- 客队总射门数
    home_pass_accuracy REAL,                             -- 主队传球成功率
    away_pass_accuracy REAL,                             -- 客队传球成功率
    home_xg REAL,                                        -- 主队预期进球
    away_xg REAL,                                        -- 客队预期进球
    home_team_rating REAL,                               -- 主队评分
    away_team_rating REAL,                               -- 客队评分
    home_avg_starting_rating REAL,                       -- 主队平均首发评分
    away_avg_starting_rating REAL,                       -- 客队平均首发评分
    home_formation VARCHAR(10),                          -- 主队阵型
    away_formation VARCHAR(10),                          -- 客队阵型

    -- B. 环境特征 (6个)
    attendance INTEGER,                                  -- 观众人数
    referee VARCHAR(100),                                -- 裁判
    venue_name VARCHAR(200),                             -- 场地名称
    raw_data_source VARCHAR(50),                         -- 数据源
    feature_extraction_version VARCHAR(20),              -- 特征提取版本
    possession_quality REAL,                             -- 控球数据质量
    xg_quality REAL,                                     -- xG数据质量
    rating_quality REAL,                                 -- 评分数据质量
    attendance_quality REAL,                             -- 观众数据质量
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),   -- 创建时间

    -- C. 深度特征 (21个)
    home_big_chances_missed INTEGER,                     -- 主队错失大机会
    away_big_chances_missed INTEGER,                     -- 客队错失大机会
    home_shots_inside_box INTEGER,                       -- 主队禁区内射门
    away_shots_inside_box INTEGER,                       -- 客队禁区内射门
    home_expected_assists REAL,                          -- 主队预期助攻
    away_expected_assists REAL,                          -- 客队预期助攻
    home_momentum_avg REAL,                              -- 主队动量平均值
    away_momentum_avg REAL,                              -- 客队动量平均值
    momentum_avg REAL,                                   -- 全场动量平均值
    momentum_std REAL,                                   -- 动量标准差
    home_passes_final_third INTEGER,                     -- 主队进攻三区传球
    away_passes_final_third INTEGER,                     -- 客队进攻三区传球
    home_ground_duels_won_pct REAL,                      -- 主队地面对抗成功率
    away_ground_duels_won_pct REAL,                      -- 客队地面对抗成功率
    home_aerial_duels_won_pct REAL,                      -- 主队空中对抗成功率
    away_aerial_duels_won_pct REAL,                      -- 客队空中对抗成功率
    home_interceptions INTEGER,                          -- 主队拦截次数
    away_interceptions INTEGER,                          -- 客队拦截次数

    -- D. 核能特征 (14个)
    home_first_sub_minute INTEGER,                       -- 主队首次换人分钟
    away_first_sub_minute INTEGER,                       -- 客队首次换人分钟
    home_sub_performance_delta REAL,                     -- 主队替补表现差值
    away_sub_performance_delta REAL,                     -- 客队替补表现差值
    formation_changed BOOLEAN,                           -- 是否发生阵型变化
    home_avg_shot_distance REAL,                         -- 主队平均射门距离
    away_avg_shot_distance REAL,                         -- 客队平均射门距离
    home_header_shot_count INTEGER,                      -- 主队头球射门次数
    away_header_shot_count INTEGER,                      -- 客队头球射门次数
    home_big_chances_ratio REAL,                         -- 主队大机会比例
    away_big_chances_ratio REAL,                         -- 客队大机会比例
    momentum_swings INTEGER,                             -- 动量切换次数
    home_defensive_density_final15 INTEGER,              -- 主队最后15分钟防守密度
    away_defensive_density_final15 INTEGER,              -- 客队最后15分钟防守密度

    -- E. 最终收割特征 (22个)
    -- 赔率与市场预期特征 (9个)
    home_opening_odds REAL,                              -- 主队初盘赔率
    draw_opening_odds REAL,                              -- 平局初盘赔率
    away_opening_odds REAL,                              -- 客队初盘赔率
    home_closing_odds REAL,                              -- 主队终盘赔率
    draw_closing_odds REAL,                              -- 平局终盘赔率
    away_closing_odds REAL,                              -- 客队终盘赔率
    home_implied_win_prob REAL,                          -- 主队隐含胜率
    odds_drift_home REAL,                                -- 主队赔率变动
    odds_drift_away REAL,                                -- 客队赔率变动

    -- 事件流深度解析特征 (9个)
    home_yellow_cards INTEGER,                           -- 主队黄牌数
    away_yellow_cards INTEGER,                           -- 客队黄牌数
    total_yellow_cards INTEGER,                          -- 总黄牌数
    home_red_cards INTEGER,                              -- 主队红牌数
    away_red_cards INTEGER,                              -- 客队红牌数
    total_red_cards INTEGER,                             -- 总红牌数
    first_red_card_minute INTEGER,                       -- 首张红牌分钟
    var_intervention_count INTEGER,                      -- VAR介入次数
    injury_stoppage_time INTEGER,                        -- 伤病中断时间

    -- 效率与守门员特征 (4个)
    home_finishing_efficiency REAL,                      -- 主队射门效率
    away_finishing_efficiency REAL,                      -- 客队射门效率
    home_saves_count INTEGER,                            -- 主队门将扑救次数
    away_saves_count INTEGER,                            -- 客队门将扑救次数

    -- 审计字段
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- 特征提取时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),   -- 更新时间

    -- 约束定义
    CONSTRAINT match_features_external_id_unique UNIQUE(external_id)
);

-- ===============================================================
-- 4. 外键约束
-- ===============================================================
-- 确保数据完整性
ALTER TABLE raw_match_data
ADD CONSTRAINT IF NOT EXISTS fk_raw_match_data_matches
FOREIGN KEY (external_id) REFERENCES matches(external_id)
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE match_features_training
ADD CONSTRAINT IF NOT EXISTS fk_match_features_training_matches
FOREIGN KEY (external_id) REFERENCES matches(external_id)
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE match_features_training
ADD CONSTRAINT IF NOT EXISTS fk_match_features_training_raw_data
FOREIGN KEY (external_id) REFERENCES raw_match_data(external_id)
ON DELETE CASCADE ON UPDATE CASCADE;

-- ===============================================================
-- 5. 性能优化索引
-- ===============================================================

-- matches 表索引
CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league_name, season);
CREATE INDEX IF NOT EXISTS idx_matches_match_time ON matches(match_time DESC);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_collection_status ON matches(collection_status)
WHERE collection_status != 'completed';
CREATE INDEX IF NOT EXISTS idx_matches_l1_collected_at ON matches(l1_collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_matches_l2_collected_at ON matches(l2_collected_at DESC);

-- raw_match_data 表索引
CREATE INDEX IF NOT EXISTS idx_raw_match_data_external_id ON raw_match_data(external_id);
CREATE INDEX IF NOT EXISTS idx_raw_match_data_parsed ON raw_match_data(parsed) WHERE parsed = FALSE;
CREATE INDEX IF NOT EXISTS idx_raw_match_data_source ON raw_match_data(source);
CREATE INDEX IF NOT EXISTS idx_raw_match_data_collected_at ON raw_match_data(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_match_data_created_at ON raw_match_data(created_at DESC);

-- JSONB 数据搜索优化索引
CREATE INDEX IF NOT EXISTS idx_raw_match_data_gin ON raw_match_data USING GIN(raw_data);
CREATE INDEX IF NOT EXISTS idx_raw_match_data_content_gin ON raw_match_data
USING GIN((raw_data->'content'));

-- match_features_training 表索引
CREATE INDEX IF NOT EXISTS idx_match_features_external_id ON match_features_training(external_id);
CREATE INDEX IF NOT EXISTS idx_match_features_extracted_at ON match_features_training(extracted_at DESC);
CREATE INDEX IF NOT EXISTS idx_match_features_home_team ON match_features_training(home_team);
CREATE INDEX IF NOT EXISTS idx_match_features_away_team ON match_features_training(away_team);
CREATE INDEX IF NOT EXISTS idx_match_features_match_time ON match_features_training(match_time DESC);

-- ===============================================================
-- 6. 自动更新时间戳触发器
-- ===============================================================

-- 创建通用的更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为matches表添加触发器
DROP TRIGGER IF EXISTS update_matches_updated_at ON matches;
CREATE TRIGGER update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为raw_match_data表添加触发器
DROP TRIGGER IF EXISTS update_raw_match_data_updated_at ON raw_match_data;
CREATE TRIGGER update_raw_match_data_updated_at
    BEFORE UPDATE ON raw_match_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为match_features_training表添加触发器
DROP TRIGGER IF EXISTS update_match_features_training_updated_at ON match_features_training;
CREATE TRIGGER update_match_features_training_updated_at
    BEFORE UPDATE ON match_features_training
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================================
-- 6. 监控视图：数据采集状态总览
-- ===============================================================
DROP VIEW IF EXISTS v_collection_status;
CREATE VIEW v_collection_status AS
SELECT
    m.external_id,
    m.league_name,
    m.season,
    m.home_team || ' vs ' || m.away_team AS match_name,
    m.match_time,
    m.status AS match_status,
    m.collection_status AS l2_collection_status,
    m.l1_collected_at,
    m.l2_collected_at,
    rmd.parsed AS l2_parsed_status,
    rmd.parse_status,
    rmd.collected_at AS l2_data_collected_at,
    rmd.data_version,
    -- 计算整体处理状态
    CASE
        WHEN m.collection_status = 'completed' AND rmd.parsed = TRUE THEN 'COMPLETED'
        WHEN m.collection_status = 'completed' AND rmd.parsed = FALSE THEN 'PENDING_PARSE'
        WHEN m.collection_status = 'in_progress' THEN 'IN_PROGRESS'
        WHEN m.collection_status = 'failed' THEN 'FAILED'
        ELSE m.collection_status
    END AS overall_status,
    -- 数据完整性检查
    CASE
        WHEN rmd.raw_data IS NOT NULL THEN 'YES'
        ELSE 'NO'
    END AS has_l2_data,
    -- 解析完整性检查
    CASE
        WHEN rmd.raw_data->'content' IS NOT NULL THEN 'YES'
        ELSE 'NO'
    END AS has_content_data
FROM matches m
LEFT JOIN raw_match_data rmd ON m.external_id = rmd.external_id
ORDER BY m.match_time DESC;

-- ===============================================================
-- 7. 数据统计视图
-- ===============================================================
DROP VIEW IF EXISTS v_collection_stats;
CREATE VIEW v_collection_stats AS
SELECT
    DATE_TRUNC('day', match_time) AS collection_date,
    COUNT(*) AS total_matches,
    COUNT(CASE WHEN collection_status = 'completed' THEN 1 END) AS l2_completed,
    COUNT(CASE WHEN rmd.external_id IS NOT NULL THEN 1 END) AS has_l2_data,
    COUNT(CASE WHEN rmd.parsed = TRUE THEN 1 END) AS l2_parsed,
    ROUND(
        COUNT(CASE WHEN collection_status = 'completed' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS l2_completion_rate,
    ROUND(
        COUNT(CASE WHEN rmd.parsed = TRUE THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS l2_parse_rate
FROM matches m
LEFT JOIN raw_match_data rmd ON m.external_id = rmd.external_id
GROUP BY DATE_TRUNC('day', match_time)
ORDER BY collection_date DESC;

-- ===============================================================
-- 8. 权限设置 (生产环境可选)
-- ===============================================================
-- 创建专用采集用户 (如果不存在)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'football_collector') THEN
--         CREATE USER football_collector WITH PASSWORD 'your_secure_password_here';
--     END IF;
-- END $$;

-- 授予权限
-- GRANT CONNECT ON DATABASE football_prediction TO football_collector;
-- GRANT USAGE ON SCHEMA public TO football_collector;
-- GRANT SELECT, INSERT, UPDATE ON matches TO football_collector;
-- GRANT SELECT, INSERT, UPDATE ON raw_match_data TO football_collector;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_collector;
-- GRANT SELECT ON v_collection_status TO football_collector;
-- GRANT SELECT ON v_collection_stats TO football_collector;

-- ===============================================================
-- 9. 初始化数据 (可选测试数据)
-- ===============================================================
-- 插入示例数据用于测试 (通常在开发环境使用)
/*
INSERT INTO matches (external_id, league_name, season, match_time, status, home_team, away_team)
VALUES
    ('test_match_001', 'Premier League', '2024/25', '2024-12-20 20:00:00+00', 'Fixture', 'Manchester United', 'Liverpool'),
    ('test_match_002', 'La Liga', '2024/25', '2024-12-21 19:30:00+00', 'Fixture', 'Real Madrid', 'Barcelona'),
    ('test_match_003', 'Bundesliga', '2024/25', '2024-12-19 18:30:00+00', 'Live', 'Bayern Munich', 'Borussia Dortmund')
ON CONFLICT (external_id) DO NOTHING;
*/

-- ===============================================================
-- 10. 表统计信息更新
-- ===============================================================
-- 更新统计信息以优化查询计划
ANALYZE matches;
ANALYZE raw_match_data;

-- ===============================================================
-- 完成提示
-- ===============================================================

-- 提交事务
COMMIT;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE 'FootballPrediction L1/L2 采集架构初始化完成';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '✅ 已创建 matches 表 (L1 索引底座)';
    RAISE NOTICE '✅ 已创建 raw_match_data 表 (L2 原始数据存储)';
    RAISE NOTICE '✅ 已添加所有必要的索引和约束';
    RAISE NOTICE '✅ 已创建监控视图 v_collection_status';
    RAISE NOTICE '✅ 已创建统计视图 v_collection_stats';
    RAISE NOTICE '✅ 已设置自动时间戳更新触发器';
    RAISE NOTICE '✅ 已更新表统计信息';
    RAISE NOTICE '';
    RAISE NOTICE '📊 监控查询示例:';
    RAISE NOTICE '   SELECT * FROM v_collection_status LIMIT 10;';
    RAISE NOTICE '   SELECT * FROM v_collection_stats;';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 架构已就绪，可以开始数据采集!';
    RAISE NOTICE '==========================================================';
    RAISE NOTICE '';
END $$;