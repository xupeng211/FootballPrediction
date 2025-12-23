-- ============================================================
-- FootballPrediction V2.0 生产级数据库 Schema
-- ============================================================
-- 版本: V2.0
-- 创建日期: 2025-12-24
-- 说明: 统一的数据库结构，包含所有必需字段和约束
-- ============================================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文搜索支持

-- ============================================================
-- 核心表：matches（比赛数据）
-- ============================================================
CREATE TABLE IF NOT EXISTS matches (
    -- === 主键 ===
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,

    -- === 基础比赛信息 ===
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    actual_result VARCHAR(10),  -- 'Home', 'Draw', 'Away'
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    venue VARCHAR(200),

    -- === 联赛和赛季 ===
    league_id INTEGER NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    season VARCHAR(10) NOT NULL,  -- '2324', '2223' 等
    is_finished BOOLEAN DEFAULT TRUE,
    status VARCHAR(50) DEFAULT 'Finished',

    -- === L2 数据版本和元数据 ===
    l2_data_version VARCHAR(20) DEFAULT 'v1.0',
    l2_data_format VARCHAR(50),  -- 'technical_features', 'home_stats_away_stats'
    collection_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(100) DEFAULT 'FotMob',

    -- === L2 特征数据 (JSONB 存储) ===
    l2_features JSONB,

    -- === 市场价格数据 ===
    market_price_home NUMERIC(10, 2),  -- 主胜赔率
    market_price_draw NUMERIC(10, 2),  -- 平局赔率
    market_price_away NUMERIC(10, 2),  -- 客胜赔率
    market_price_updated_at TIMESTAMP WITH TIME ZONE,

    -- === 元数据 ===
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- === 约束 ===
    CONSTRAINT check_result CHECK (actual_result IN ('Home', 'Draw', 'Away', NULL)),
    CONSTRAINT check_scores CHECK (home_score >= 0 AND away_score >= 0),
    CONSTRAINT check_market_prices CHECK (
        (market_price_home IS NULL AND market_price_draw IS NULL AND market_price_away IS NULL) OR
        (market_price_home > 0 AND market_price_draw > 0 AND market_price_away > 0)
    )
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league_id, season);
CREATE INDEX IF NOT EXISTS idx_matches_match_time ON matches(match_time DESC);
CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team);
CREATE INDEX IF NOT EXISTS idx_matches_l2_features ON matches USING GIN(l2_features);
CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);

-- ============================================================
-- 触发器：自动更新 updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_matches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_matches_updated_at_trigger ON matches;
CREATE TRIGGER update_matches_updated_at_trigger
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_matches_updated_at();

-- ============================================================
-- 视图：活跃赛季数据
-- ============================================================
CREATE OR REPLACE VIEW active_seasons AS
SELECT
    league_id,
    league_name,
    season,
    COUNT(*) as total_matches,
    MIN(match_time) as earliest_match,
    MAX(match_time) as latest_match,
    COUNT(CASE WHEN l2_features IS NOT NULL THEN 1 END) as matches_with_features,
    COUNT(CASE WHEN market_price_home IS NOT NULL THEN 1 END) as matches_with_prices
FROM matches
WHERE is_finished = TRUE
GROUP BY league_id, league_name, season
ORDER BY season DESC, league_name;

-- ============================================================
-- 联赛配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS league_config (
    league_id SERIAL PRIMARY KEY,
    league_name VARCHAR(100) UNIQUE NOT NULL,
    league_code VARCHAR(20) UNIQUE NOT NULL,  -- 'EPL', 'CHAMPIONSHIP'
    fotmob_league_id INTEGER,  -- FotMob API 中的联赛ID
    is_active BOOLEAN DEFAULT TRUE,
    tier VARCHAR(20),  -- 'Tier1', 'Tier2', 'Tier3'
    data_quality_threshold INTEGER DEFAULT 20000  -- 哨兵阈值（字节）
);

-- ============================================================
-- 初始数据：联赛配置
-- ============================================================
INSERT INTO league_config (league_name, league_code, fotmob_league_id, tier, data_quality_threshold) VALUES
('Premier League', 'EPL', 47, 'Tier1', 100000),
('Championship', 'CHAMPIONSHIP', 48, 'Tier2', 50000),
('La Liga', 'LALIGA', 8, 'Tier1', 100000),
('Bundesliga', 'BUNDESLIGA', 54, 'Tier1', 100000),
('Serie A', 'SERIEA', 23, 'Tier1', 100000),
('Ligue 1', 'LIGUE1', 34, 'Tier1', 100000),
('Eredivisie', 'EREDIVISIE', 13, 'Tier2', 50000),
('Primeira Liga', 'PRIMEIRA_LIGA', 61, 'Tier2', 50000),
('Serie B', 'SERIEB', 57, 'Tier3', 20000),
('2. Bundesliga', 'BUNDESLIGA_2', 55, 'Tier3', 20000)
ON CONFLICT (league_code) DO NOTHING;

-- ============================================================
-- 说明
-- ============================================================
-- 1. league_id: 内部联赛ID（自增主键）
-- 2. fotmob_league_id: FotMob API 中的联赛ID（用于API调用）
-- 3. tier: 联赛等级，用于哨兵机制阈值设置
-- 4. data_quality_threshold: 数据质量阈值（字节），用于哨兵机制
-- ============================================================
