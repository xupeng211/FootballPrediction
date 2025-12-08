-- 标准化的 match_advanced_stats 表结构
-- PostgreSQL 混合存储：可索引列 + JSONB深度学习特征

-- 创建标准化的高阶统计数据表
CREATE TABLE IF NOT EXISTS match_advanced_stats (
    -- 主键标识
    match_id VARCHAR(100) PRIMARY KEY,

    -- === 核心指标 - 可索引列 (用于 SQL 快速筛选) ===
    -- 比赛元数据
    referee VARCHAR(200),                      -- 裁判姓名
    stadium VARCHAR(200),                      -- 球场名称
    weather VARCHAR(100),                      -- 天气情况
    attendance INTEGER,                         -- 观众人数

    -- 期望进球 (Expected Goals) - ML模型核心特征
    home_xg DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    away_xg DECIMAL(5,2) NOT NULL DEFAULT 0.0,

    -- 基础技术统计
    possession_home INTEGER NOT NULL DEFAULT 0,    -- 控球率(整数形式，如58表示58%)
    possession_away INTEGER NOT NULL DEFAULT 0,
    shots_home INTEGER NOT NULL DEFAULT 0,
    shots_away INTEGER NOT NULL DEFAULT 0,
    shots_on_target_home INTEGER NOT NULL DEFAULT 0,
    shots_on_target_away INTEGER NOT NULL DEFAULT 0,

    -- 犯规统计
    fouls_home INTEGER NOT NULL DEFAULT 0,
    fouls_away INTEGER NOT NULL DEFAULT 0,
    yellow_cards_home INTEGER NOT NULL DEFAULT 0,
    yellow_cards_away INTEGER NOT NULL DEFAULT 0,
    red_cards_home INTEGER NOT NULL DEFAULT 0,
    red_cards_away INTEGER NOT NULL DEFAULT 0,

    -- 定位球统计
    corners_home INTEGER NOT NULL DEFAULT 0,
    corners_away INTEGER NOT NULL DEFAULT 0,
    offsides_home INTEGER NOT NULL DEFAULT 0,
    offsides_away INTEGER NOT NULL DEFAULT 0,

    -- === 深度学习特征 - JSONB存储 (用于 AI 训练) ===
    -- 完整射门地图数据
    shot_map JSONB NOT NULL DEFAULT '[]',

    -- 全场压力指数时间序列 (用于momentum分析)
    momentum JSONB NOT NULL DEFAULT '{}',

    -- 完整阵容数据 (首发+替补，含球员评分、位置信息)
    lineups JSONB NOT NULL DEFAULT '{}',

    -- 详细的球员技术统计 (评分、传球、对抗等个人表现数据)
    player_stats JSONB NOT NULL DEFAULT '{}',

    -- 完整的比赛事件时间轴 (进球、换人、卡牌、VAR等所有事件)
    match_events JSONB NOT NULL DEFAULT '[]',

    -- 文字直播流 (如果API提供)
    ticker JSONB NOT NULL DEFAULT '{}',

    -- === 数据质量和来源追踪 ===
    data_quality_score DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    source_reliability VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- 时间戳
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 数据完整性约束
    CONSTRAINT chk_shot_map_is_array CHECK (jsonb_typeof(shot_map) = 'array'),
    CONSTRAINT chk_momentum_is_object CHECK (jsonb_typeof(momentum) = 'object'),
    CONSTRAINT chk_lineups_is_object CHECK (jsonb_typeof(lineups) = 'object'),
    CONSTRAINT chk_player_stats_is_object CHECK (jsonb_typeof(player_stats) = 'object'),
    CONSTRAINT chk_match_events_is_array CHECK (jsonb_typeof(match_events) = 'array'),
    CONSTRAINT chk_ticker_is_object CHECK (jsonb_typeof(ticker) = 'object')
);

-- =====================================================
-- 索引策略优化 - 平衡查询性能和存储效率
-- =====================================================

-- JSONB字段专用索引 (支持GIN索引，加速JSONB查询)
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_shot_map ON match_advanced_stats USING GIN (shot_map);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_momentum ON match_advanced_stats USING GIN (momentum);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_lineups ON match_advanced_stats USING GIN (lineups);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_player_stats ON match_advanced_stats USING GIN (player_stats);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_match_events ON match_advanced_stats USING GIN (match_events);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_ticker ON match_advanced_stats USING GIN (ticker);

-- 常用查询索引 (加速筛选和排序)
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_referee ON match_advanced_stats(referee);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_stadium ON match_advanced_stats(stadium);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_weather ON match_advanced_stats(weather);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_attendance ON match_advanced_stats(attendance);

-- ML模型查询优化索引
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_home_xg ON match_advanced_stats(home_xg);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_away_xg ON match_advanced_stats(away_xg);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_possession_home ON match_advanced_stats(possession_home);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_possession_away ON match_advanced_stats(possession_away);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_shots_total ON match_advanced_stats(shots_home, shots_away);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_xg_total ON match_advanced_stats(home_xg + away_xg);

-- 复合索引 (常见查询组合)
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_xg_possession ON match_advanced_stats(home_xg, away_xg, possession_home, possession_away);

-- 时间戳索引
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_created_at ON match_advanced_stats(created_at);
CREATE INDEX IF NOT EXISTS idx_match_advanced_stats_updated_at ON match_advanced_stats(updated_at);

-- =====================================================
-- 表和字段注释 (数据字典)
-- =====================================================

COMMENT ON TABLE match_advanced_stats IS 'ML/DL优化的比赛高阶统计数据表 - 混合存储设计：可索引列 + JSONB深度学习特征，适用于机器学习模型训练和足球数据分析';

COMMENT ON COLUMN match_advanced_stats.match_id IS '主键：FotMob比赛唯一标识符';
COMMENT ON COLUMN match_advanced_stats.referee IS '裁判姓名：比赛主裁判的完整姓名';
COMMENT ON COLUMN match_advanced_stats.stadium IS '球场名称：比赛举办球场的完整名称';
COMMENT ON COLUMN match_advanced_stats.weather IS '天气情况：比赛当天的天气状况';
COMMENT ON COLUMN match_advanced_stats.attendance IS '观众人数：现场观看比赛的总观众数量';
COMMENT ON COLUMN match_advanced_stats.home_xg IS '主队期望进球数(xG)：基于射门数据的期望进球值，机器学习核心特征';
COMMENT ON COLUMN match_advanced_stats.away_xg IS '客队期望进球数(xG)：基于射门数据的期望进球值，机器学习核心特征';
COMMENT ON COLUMN match_advanced_stats.possession_home IS '主队控球率(整数)：比赛期间主队控球百分比，如58表示58%';
COMMENT ON COLUMN match_advanced_stats.possession_away IS '客队控球率(整数)：比赛期间客队控球百分比';
COMMENT ON COLUMN match_advanced_stats.shot_map IS '射门地图(JSONB)：包含每个射门的位置坐标(x,y)、期望进球值、射门类型、时间戳等深度学习特征';
COMMENT ON COLUMN match_advanced_stats.momentum IS '压力指数(JSONB)：全场比赛压力指数的时间序列数据，用于momentum分析';
COMMENT ON COLUMN match_advanced_stats.lineups IS '阵容信息(JSONB)：完整阵容数据，包含首发名单、替补球员、阵型、球员评分等';
COMMENT ON COLUMN match_advanced_stats.player_stats IS '球员统计(JSONB)：详细的个人技术统计数据，包含评分、传球、对抗、射门等各项指标';
COMMENT ON COLUMN match_advanced_stats.match_events IS '比赛事件(JSONB)：完整的事件时间轴，包含进球、换人、黄红牌、VAR等所有事件';
COMMENT ON COLUMN match_advanced_stats.ticker IS '文字直播流(JSONB)：比赛的实时文字播报数据';
COMMENT ON COLUMN match_advanced_stats.data_quality_score IS '数据质量评分(0-1)：基于数据完整性、一致性的自动评估指标';
COMMENT ON COLUMN match_advanced_stats.source_reliability IS '数据来源可靠性：high/medium/low三级可靠性评估';

-- 验证表创建成功
SELECT '✅ 标准化 match_advanced_stats 表创建成功!' AS status, NOW() AS created_at;