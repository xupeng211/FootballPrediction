-- ============================================
-- FootballPrediction V25.1 - 数据库初始化脚本
-- ============================================
-- 版本: V25.1
-- 生成时间: 2025-12-26
-- 用途: Docker 容器启动时自动执行
-- ============================================

-- 设置编码
SET client_encoding = 'UTF8';

-- ============================================
-- 扩展安装
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文搜索支持

-- ============================================
-- 核心表: matches (比赛基础数据)
-- ============================================
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(50) PRIMARY KEY,
    external_id VARCHAR(100),
    league_name VARCHAR(100) NOT NULL DEFAULT 'Premier League',
    season VARCHAR(20) NOT NULL DEFAULT '2324',
    home_team VARCHAR(200) NOT NULL,
    away_team VARCHAR(200) NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    actual_result VARCHAR(10),  -- home/draw/away
    match_date TIMESTAMP WITH TIME ZONE,
    venue VARCHAR(200),
    status VARCHAR(50) DEFAULT 'Scheduled',
    is_finished BOOLEAN DEFAULT false,
    collection_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- V25.1 元数据
    data_version VARCHAR(20) DEFAULT 'V25.1',
    data_source VARCHAR(50) DEFAULT 'FotMob',
    -- 索引优化
    CONSTRAINT valid_scores CHECK (
        (home_score IS NULL AND away_score IS NULL) OR
        (home_score >= 0 AND away_score >= 0)
    )
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date DESC);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_finished ON matches(is_finished) WHERE is_finished = true;

-- ============================================
-- 核心表: raw_match_data (L2 原始数据)
-- ============================================
CREATE TABLE IF NOT EXISTS raw_match_data (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    external_id VARCHAR(100),
    raw_data JSONB NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR(20) DEFAULT 'V26.1',
    data_hash VARCHAR(64),  -- SHA256 校验
    UNIQUE(match_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_raw_data_match_id ON raw_match_data(match_id);
CREATE INDEX IF NOT EXISTS idx_raw_data_collected_at ON raw_match_data(collected_at DESC);
-- JSONB 索引
CREATE INDEX IF NOT EXISTS idx_raw_data_gin ON raw_match_data USING GIN(raw_data);

-- ============================================
-- 核心表: match_features_training (V25.1 特征数据)
-- ============================================
CREATE TABLE IF NOT EXISTS match_features_training (
    match_id VARCHAR(50) PRIMARY KEY REFERENCES matches(match_id) ON DELETE CASCADE,
    season VARCHAR(20) NOT NULL,
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team VARCHAR(200) NOT NULL,
    away_team VARCHAR(200) NOT NULL,
    actual_result VARCHAR(10),
    feature_version VARCHAR(20) DEFAULT 'V25.1',
    -- V17.0 滚动特征 (16维)
    rolling_xg_home FLOAT,
    rolling_xg_away FLOAT,
    rolling_shots_on_target_home FLOAT,
    rolling_shots_on_target_away FLOAT,
    rolling_possession_home FLOAT,
    rolling_possession_away FLOAT,
    rolling_team_rating_home FLOAT,
    rolling_team_rating_away FLOAT,
    -- V18.0 赛前特征 (8维)
    home_table_position INTEGER,
    away_table_position INTEGER,
    table_position_diff INTEGER,
    home_points FLOAT,
    away_points FLOAT,
    points_diff FLOAT,
    home_recent_form_points FLOAT,
    away_recent_form_points FLOAT,
    -- V19.0 高级动态特征 (13维)
    raw_elo_gap FLOAT,
    adjusted_elo_gap FLOAT,
    fatigue_impact FLOAT,
    schedule_impact FLOAT,
    home_fatigue_index FLOAT,
    away_fatigue_index FLOAT,
    fatigue_diff FLOAT,
    home_rest_days FLOAT,
    away_rest_days FLOAT,
    home_relegation_incentive FLOAT,
    away_relegation_incentive FLOAT,
    incentive_diff FLOAT,
    home_desperation FLOAT,
    -- V19.4 平局敏感度特征 (3维)
    table_proximity FLOAT,
    low_scoring_tendency FLOAT,
    elo_diff_cluster FLOAT,
    -- V25.1 自适应特征存储 (JSONB)
    adaptive_features JSONB,  -- 12061维自适应特征
    feature_count INTEGER DEFAULT 0,  -- 特征数量统计
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_features_season ON match_features_training(season);
CREATE INDEX IF NOT EXISTS idx_features_date ON match_features_training(match_date DESC);
CREATE INDEX IF NOT EXISTS idx_features_version ON match_features_training(feature_version);
-- JSONB 索引 (自适应特征)
CREATE INDEX IF NOT EXISTS idx_features_adaptive_gin ON match_features_training USING GIN(adaptive_features);

-- ============================================
-- 核心表: league_config (联赛配置)
-- ============================================
CREATE TABLE IF NOT EXISTS league_config (
    league_id SERIAL PRIMARY KEY,
    league_name VARCHAR(100) UNIQUE NOT NULL,
    league_code VARCHAR(64) UNIQUE,
    fotmob_id VARCHAR(50),
    country VARCHAR(100),
    season_mapping JSONB,  -- {"2324": "23/24", "2223": "22/23"}
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,  -- 采集优先级
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 初始化默认联赛
INSERT INTO league_config (league_name, league_code, fotmob_id, country, priority)
VALUES
    ('Premier League', 'ENGLAND_PREMIER_LEAGUE', 'ENGLAND:Premier League', 'England', 1),
    ('La Liga', 'SPAIN_LA_LIGA', 'SPAIN:La Liga', 'Spain', 2),
    ('Bundesliga', 'GERMANY_BUNDESLIGA', 'GERMANY:Bundesliga', 'Germany', 3),
    ('Serie A', 'ITALY_SERIE_A', 'ITALY:Serie A', 'Italy', 4),
    ('Ligue 1', 'FRANCE_LIGUE_1', 'FRANCE:Ligue 1', 'France', 5)
ON CONFLICT (league_name) DO NOTHING;

-- ============================================
-- 核心表: odds (赔率数据)
-- ============================================
CREATE TABLE IF NOT EXISTS odds (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    bookmaker VARCHAR(100) NOT NULL,
    home_odds FLOAT,
    draw_odds FLOAT,
    away_odds FLOAT,
    over_25_odds FLOAT,
    btts_odds FLOAT,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, bookmaker)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker);

-- ============================================
-- 核心表: predictions (预测结果)
-- ============================================
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    model_version VARCHAR(20) NOT NULL,
    predicted_result VARCHAR(10) NOT NULL,  -- home/draw/away
    confidence_home FLOAT,
    confidence_draw FLOAT,
    confidence_away FLOAT,
    final_confidence FLOAT,  -- 最高概率
    edge FLOAT,  -- EV 边缘
    recommended_bet VARCHAR(50),
    prediction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_correct BOOLEAN,
    UNIQUE(match_id, model_version)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_version ON predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_correct ON predictions(is_correct);

-- ============================================
-- V25.1 新表: feature_registry (特征注册表)
-- ============================================
CREATE TABLE IF NOT EXISTS feature_registry (
    feature_id SERIAL PRIMARY KEY,
    feature_path VARCHAR(200) UNIQUE NOT NULL,  -- 例如: "home_team__stats__xg"
    feature_name VARCHAR(100),
    data_type VARCHAR(20),  -- int/float/bool/percentage
    source_path VARCHAR(500),  -- JSON 源路径
    is_active BOOLEAN DEFAULT true,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- V25.1 新表: data_collection_log (数据采集日志)
-- ============================================
CREATE TABLE IF NOT EXISTS data_collection_log (
    id BIGSERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,  -- harvest/parse/extract
    match_id VARCHAR(50),
    status VARCHAR(20) NOT NULL,  -- success/failure/skipped
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_collection_log_operation ON data_collection_log(operation_type);
CREATE INDEX IF NOT EXISTS idx_collection_log_status ON data_collection_log(status);
CREATE INDEX IF NOT EXISTS idx_collection_log_created ON data_collection_log(created_at DESC);

-- ============================================
-- 数据库函数: 更新 updated_at 字段
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要更新时间戳的表创建触发器
CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_features_updated_at BEFORE UPDATE ON match_features_training
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_league_config_updated_at BEFORE UPDATE ON league_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 权限设置 (Docker 环境)
-- ============================================
-- 确保应用用户有权限
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO football_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO football_user;

-- ============================================
-- 完成
-- ============================================
-- 数据库初始化完成
-- 版本: V25.1
-- 表数量: 9
-- 索引数量: 30+
-- ============================================
