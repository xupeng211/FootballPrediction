-- ============================================
-- V51.1 特征库架构升级 - 数据库表创建脚本
-- ============================================
-- 创建日期: 2025-12-31
-- 版本: V51.1
-- 说明: 创建特征快照表、赛前特征表和特征注册表
-- ============================================

-- ============================================
-- 表 1: 特征快照表 (feature_snapshots)
-- 用途: 存储 V51 提取的 642 维原始"赛后表现"特征
-- ============================================
CREATE TABLE IF NOT EXISTS feature_snapshots (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 提取元数据
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extractor_config JSONB,  -- 提取器配置快照

    -- V51.0 原始特征 (JSONB 存储，支持 642 维)
    raw_features JSONB NOT NULL,  -- {feature_path: value}
    feature_count INTEGER NOT NULL,  -- 特征数量

    -- 质量指标
    extraction_status VARCHAR(20) NOT NULL DEFAULT 'success',  -- success/partial/failed
    quality_score FLOAT,  -- 0.0-1.0，特征完整性评分
    null_count INTEGER DEFAULT 0,  -- NULL 值数量
    blacklist_filtered INTEGER DEFAULT 0,  -- 黑名单过滤数量

    -- 错误信息
    error_message TEXT,
    processing_time_ms INTEGER,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT valid_quality_score CHECK (quality_score BETWEEN 0 AND 1),
    CONSTRAINT valid_feature_count CHECK (feature_count >= 0)
);

-- 性能索引
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_match_id
    ON feature_snapshots(match_id);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_extracted_at
    ON feature_snapshots(extracted_at DESC);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_status
    ON feature_snapshots(extraction_status);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_quality
    ON feature_snapshots(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_version
    ON feature_snapshots(feature_version);

-- JSONB GIN 索引 (支持特征查询)
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_features_gin
    ON feature_snapshots USING GIN(raw_features);

-- 唯一约束 (同一 match_id + version 只保留最新)
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_snapshots_unique
    ON feature_snapshots(match_id, feature_version);

-- ============================================
-- 表 2: 赛前特征表 (prematch_features)
-- 用途: 存储计算好的赛前预测信号 (滚动统计)
-- ============================================
CREATE TABLE IF NOT EXISTS prematch_features (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 比赛基础信息 (用于快速查询)
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team VARCHAR(200) NOT NULL,
    away_team VARCHAR(200) NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    season VARCHAR(20) NOT NULL,

    -- ============================================
    -- 第一类: 实力底蕴特征 (Past 10 matches average)
    -- ============================================
    -- 主队实力 (过去 10 场平均)
    home_rolling_xg FLOAT,              -- xG 平均值
    home_rolling_xg_std FLOAT,          -- xG 标准差
    home_rolling_shots_on_target FLOAT, -- 射正平均
    home_rolling_shots_on_target_std FLOAT,
    home_rolling_possession FLOAT,      -- 控球率平均
    home_rolling_possession_std FLOAT,
    home_rolling_team_rating FLOAT,     -- 评分平均
    home_rolling_team_rating_std FLOAT,

    -- 客队实力 (过去 10 场平均)
    away_rolling_xg FLOAT,
    away_rolling_xg_std FLOAT,
    away_rolling_shots_on_target FLOAT,
    away_rolling_shots_on_target_std FLOAT,
    away_rolling_possession FLOAT,
    away_rolling_possession_std FLOAT,
    away_rolling_team_rating FLOAT,
    away_rolling_team_rating_std FLOAT,

    -- 实力差值
    rolling_xg_diff FLOAT,              -- 主队 xG - 客队 xG
    rolling_possession_diff FLOAT,      -- 主队控球 - 客队控球
    rolling_rating_diff FLOAT,          -- 主队评分 - 客队评分

    -- ============================================
    -- 第二类: 即时状态特征 (Past 3 matches trend)
    -- ============================================
    -- 主队近期状态 (过去 3 场)
    home_recent_form_points FLOAT,     -- 积分: 3分/胜, 1分/平, 0分/负
    home_recent_goals_scored FLOAT,    -- 进球数
    home_recent_goals_conceded FLOAT,  -- 失球数
    home_recent_win_rate FLOAT,        -- 胜率
    home_recent_trend VARCHAR(10),      -- 'ascending'/'descending'/'stable'

    -- 客队近期状态 (过去 3 场)
    away_recent_form_points FLOAT,
    away_recent_goals_scored FLOAT,
    away_recent_goals_conceded FLOAT,
    away_recent_win_rate FLOAT,
    away_recent_trend VARCHAR(10),

    -- 状态对比
    recent_form_diff FLOAT,             -- 主队积分 - 客队积分
    momentum_gap FLOAT,                 -- 势能差值

    -- ============================================
    -- 第三类: 主/客场特定偏见特征 (Venue-specific)
    -- ============================================
    -- 主队主场表现 (过去 10 场主场)
    home_home_win_rate FLOAT,          -- 主场胜率
    home_home_goals_scored FLOAT,      -- 主场进球
    home_home_goals_conceded FLOAT,    -- 主场失球
    home_home_clean_sheets FLOAT,      -- 主场零封

    -- 主队客场表现 (过去 10 场客场)
    home_away_win_rate FLOAT,
    home_away_goals_scored FLOAT,
    home_away_goals_conceded FLOAT,
    home_away_clean_sheets FLOAT,

    -- 客队主场表现 (过去 10 场主场)
    away_home_win_rate FLOAT,
    away_home_goals_scored FLOAT,
    away_home_goals_conceded FLOAT,
    away_home_clean_sheets FLOAT,

    -- 客队客场表现 (过去 10 场客场)
    away_away_win_rate FLOAT,
    away_away_goals_scored FLOAT,
    away_away_goals_conceded FLOAT,
    away_away_clean_sheets FLOAT,

    -- 主客场优势
    home_advantage FLOAT,              -- 主队主场胜率 - 客队客场胜率
    venue_bias FLOAT,                  -- 主场偏向度

    -- ============================================
    -- 第四类: 竞技压力特征 (Match density/Rest days)
    -- ============================================
    -- 疲劳度指数
    home_fatigue_index FLOAT,          -- 过去 7 天比赛密度
    away_fatigue_index FLOAT,
    fatigue_diff FLOAT,                -- 主队疲劳 - 客队疲劳

    -- 休息天数
    home_rest_days FLOAT,              -- 距离上一场休息天数
    away_rest_days FLOAT,
    rest_days_diff FLOAT,              -- 休息天数差

    -- 赛程密度
    home_matches_7days INTEGER,        -- 过去 7 天比赛数
    away_matches_7days INTEGER,
    home_matches_30days INTEGER,       -- 过去 30 天比赛数
    away_matches_30days INTEGER,

    -- ============================================
    -- 第五类: 积分榜特征 (来自 schema_manager.py)
    -- ============================================
    home_table_position INTEGER,
    away_table_position INTEGER,
    table_position_diff INTEGER,
    home_points FLOAT,
    away_points FLOAT,
    points_diff FLOAT,
    -- 注: recent_form_points 已在第二类中定义，此处不重复

    -- ============================================
    -- 第六类: ELO 评分特征
    -- ============================================
    raw_elo_gap FLOAT,
    adjusted_elo_gap FLOAT,            -- 调整主场优势

    -- ============================================
    -- 元数据与审计
    -- ============================================
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    computation_window VARCHAR(20) NOT NULL DEFAULT 'past_10_matches',

    -- 质量指标
    home_history_count INTEGER,        -- 主队历史比赛数
    away_history_count INTEGER,        -- 客队历史比赛数
    min_history_required INTEGER DEFAULT 5,  -- 最低历史要求
    is_valid BOOLEAN DEFAULT TRUE,     -- 是否满足最低历史要求

    -- 计算性能
    processing_time_ms INTEGER,

    -- 约束
    CONSTRAINT valid_win_rate CHECK (
        home_home_win_rate BETWEEN 0 AND 1 AND
        away_away_win_rate BETWEEN 0 AND 1
    ),
    CONSTRAINT valid_fatigue_index CHECK (
        home_fatigue_index BETWEEN 0 AND 1 AND
        away_fatigue_index BETWEEN 0 AND 1
    )
);

-- ============================================
-- 性能优化索引 (关键查询路径)
-- ============================================
-- 按球队查询 (用于计算滚动特征)
CREATE INDEX IF NOT EXISTS idx_prematch_home_team_date
    ON prematch_features(home_team, match_date DESC);
CREATE INDEX IF NOT EXISTS idx_prematch_away_team_date
    ON prematch_features(away_team, match_date DESC);

-- 按联赛和赛季查询
CREATE INDEX IF NOT EXISTS idx_prematch_league_season
    ON prematch_features(league_name, season, match_date DESC);

-- 按日期范围查询
CREATE INDEX IF NOT EXISTS idx_prematch_match_date
    ON prematch_features(match_date DESC);

-- 质量过滤
CREATE INDEX IF NOT EXISTS idx_prematch_is_valid
    ON prematch_features(is_valid) WHERE is_valid = TRUE;

-- 版本管理
CREATE INDEX IF NOT EXISTS idx_prematch_version
    ON prematch_features(feature_version);

-- 唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_prematch_unique
    ON prematch_features(match_id, feature_version);

-- ============================================
-- 表 3: 特征注册表 (feature_registry)
-- 用途: 记录所有特征的元数据和血缘关系
-- ============================================
CREATE TABLE IF NOT EXISTS feature_registry (
    id SERIAL PRIMARY KEY,

    -- 特征标识
    feature_path VARCHAR(200) UNIQUE NOT NULL,  -- 例如: "header_content_stats__home_xg"
    feature_name VARCHAR(100) NOT NULL,         -- 例如: "rolling_xg_home"
    feature_category VARCHAR(50),               -- 'raw'/'derived'/'prematch'

    -- 数据类型
    data_type VARCHAR(20) NOT NULL,             -- 'int'/'float'/'bool'/'percentage'
    value_range VARCHAR(50),                    -- 例如: "0.0-1.0" 或 "0-100"

    -- 来源追溯
    source_path VARCHAR(500),                   -- JSON 源路径
    source_table VARCHAR(100),                  -- 'feature_snapshots'/'prematch_features'

    -- 计算逻辑
    computation_logic TEXT,                     -- SQL/Python 伪代码
    dependencies TEXT[],                        -- 依赖的其他特征

    -- 质量指标
    is_active BOOLEAN DEFAULT TRUE,
    null_rate FLOAT DEFAULT 0,                 -- NULL 值比例
    distribution_stats JSONB,                  -- {mean, std, min, max, median}

    -- 版本管理
    feature_version VARCHAR(20) DEFAULT 'V51.1',
    introduced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP WITH TIME ZONE,

    -- 审计
    created_by VARCHAR(100) DEFAULT 'system',
    last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_feature_registry_path
    ON feature_registry(feature_path);
CREATE INDEX IF NOT EXISTS idx_feature_registry_category
    ON feature_registry(feature_category);
CREATE INDEX IF NOT EXISTS idx_feature_registry_active
    ON feature_registry(is_active) WHERE is_active = TRUE;

-- ============================================
-- 数据库修复: 移除冗余 external_id 字段
-- ============================================
-- 注意: 根据审计报告，matches.external_id 与 match_id 冗余
-- 此处暂时保留，待数据迁移完成后再删除
-- ALTER TABLE matches DROP COLUMN IF EXISTS external_id;
