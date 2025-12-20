-- 简化版表创建脚本
BEGIN;

-- 创建 matches 表
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) NOT NULL UNIQUE,
    league_name VARCHAR(100) NOT NULL,
    season VARCHAR(20) NOT NULL,
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Fixture',
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    collection_status VARCHAR(20) DEFAULT 'pending',
    league_id INTEGER,
    home_team_id INTEGER,
    away_team_id INTEGER,
    venue_name VARCHAR(200),
    result_score VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    l1_collected_at TIMESTAMP WITH TIME ZONE,
    l2_collected_at TIMESTAMP WITH TIME ZONE
);

-- 创建 raw_match_data 表
CREATE TABLE raw_match_data (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) NOT NULL UNIQUE,
    raw_data JSONB NOT NULL,
    source VARCHAR(50) DEFAULT 'fotmob',
    data_version INTEGER DEFAULT 1,
    parsed BOOLEAN DEFAULT FALSE,
    parse_status VARCHAR(20) DEFAULT 'pending',
    parse_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建基本索引
CREATE INDEX idx_matches_external_id ON matches(external_id);
CREATE INDEX idx_matches_league_season ON matches(league_name, season);
CREATE INDEX idx_matches_collection_status ON matches(collection_status);
CREATE INDEX idx_raw_match_data_external_id ON raw_match_data(external_id);

-- 创建监控视图
CREATE VIEW v_collection_status AS
SELECT
    m.external_id,
    m.league_name,
    m.season,
    m.home_team || ' vs ' || m.away_team AS match_name,
    m.match_time,
    m.status AS match_status,
    m.collection_status,
    m.l1_collected_at,
    m.l2_collected_at,
    CASE
        WHEN rmd.raw_data IS NOT NULL THEN 'YES'
        ELSE 'NO'
    END AS has_l2_data
FROM matches m
LEFT JOIN raw_match_data rmd ON m.external_id = rmd.external_id
ORDER BY m.match_time DESC;

COMMIT;