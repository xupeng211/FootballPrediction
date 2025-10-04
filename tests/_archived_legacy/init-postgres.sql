-- Legacy 测试数据库初始化脚本

-- 创建测试数据库（如果不存在）
-- CREATE DATABASE IF NOT EXISTS football_test;

-- 使用数据库
-- \c football_test;

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建示例表结构
CREATE TABLE IF NOT EXISTS leagues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    league_id INTEGER REFERENCES leagues(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    match_date TIMESTAMP,
    league_id INTEGER REFERENCES leagues(id),
    status VARCHAR(20) DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    predicted_home_score INTEGER,
    predicted_away_score INTEGER,
    actual_home_score INTEGER,
    actual_away_score INTEGER,
    confidence DECIMAL(5,2),
    model_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);

-- 插入测试数据
INSERT INTO leagues (name, country) VALUES
    ('Premier League', 'England'),
    ('La Liga', 'Spain'),
    ('Bundesliga', 'Germany')
ON CONFLICT DO NOTHING;

INSERT INTO teams (name, league_id) VALUES
    ('Manchester United', 1),
    ('Liverpool', 1),
    ('Barcelona', 2),
    ('Real Madrid', 2),
    ('Bayern Munich', 3),
    ('Borussia Dortmund', 3)
ON CONFLICT DO NOTHING;

-- 授权给测试用户
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;