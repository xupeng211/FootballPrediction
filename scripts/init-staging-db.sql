-- =================================================================
-- 本地试运营环境数据库初始化脚本
-- Local Staging Database Initialization Script
-- =================================================================

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建基础表结构（如果不存在）
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建预测表
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    match_id INTEGER NOT NULL,
    prediction_data JSONB NOT NULL,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建比赛表
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    match_date TIMESTAMP NOT NULL,
    league VARCHAR(100),
    actual_score VARCHAR(10),
    status VARCHAR(20) DEFAULT 'upcoming',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为表添加更新时间触发器
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_predictions_updated_at
    BEFORE UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据
INSERT INTO matches (home_team, away_team, match_date, league, status) VALUES
('Manchester United', 'Liverpool', CURRENT_TIMESTAMP + INTERVAL '1 day', 'Premier League', 'upcoming'),
('Barcelona', 'Real Madrid', CURRENT_TIMESTAMP + INTERVAL '2 days', 'La Liga', 'upcoming'),
('Bayern Munich', 'Borussia Dortmund', CURRENT_TIMESTAMP + INTERVAL '3 days', 'Bundesliga', 'upcoming'),
('PSG', 'Lyon', CURRENT_TIMESTAMP + INTERVAL '4 days', 'Ligue 1', 'upcoming'),
('Inter Milan', 'AC Milan', CURRENT_TIMESTAMP + INTERVAL '5 days', 'Serie A', 'upcoming')
ON CONFLICT DO NOTHING;

-- 插入示例球队数据
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    league VARCHAR(100),
    country VARCHAR(50),
    founded_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO teams (name, league, country, founded_year) VALUES
('Manchester United', 'Premier League', 'England', 1878),
('Liverpool', 'Premier League', 'England', 1892),
('Barcelona', 'La Liga', 'Spain', 1899),
('Real Madrid', 'La Liga', 'Spain', 1902),
('Bayern Munich', 'Bundesliga', 'Germany', 1900),
('Borussia Dortmund', 'Bundesliga', 'Germany', 1909),
('PSG', 'Ligue 1', 'France', 1970),
('Lyon', 'Ligue 1', 'France', 1950),
('Inter Milan', 'Serie A', 'Italy', 1908),
('AC Milan', 'Serie A', 'Italy', 1899)
ON CONFLICT DO NOTHING;

-- 创建联赛表
CREATE TABLE IF NOT EXISTS leagues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    country VARCHAR(50),
    founded_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO leagues (name, country, founded_year) VALUES
('Premier League', 'England', 1992),
('La Liga', 'Spain', 1929),
('Bundesliga', 'Germany', 1963),
('Ligue 1', 'France', 1932),
('Serie A', 'Italy', 1898)
ON CONFLICT DO NOTHING;

-- 创建视图用于常用查询
CREATE OR REPLACE VIEW match_predictions AS
SELECT
    m.id as match_id,
    m.home_team,
    m.away_team,
    m.match_date,
    m.league,
    m.status,
    COUNT(p.id) as prediction_count,
    AVG(p.confidence_score) as avg_confidence
FROM matches m
LEFT JOIN predictions p ON m.id = p.match_id
GROUP BY m.id, m.home_team, m.away_team, m.match_date, m.league, m.status;

-- 创建用户统计视图
CREATE OR REPLACE VIEW user_statistics AS
SELECT
    u.id,
    u.username,
    u.email,
    COUNT(p.id) as total_predictions,
    AVG(p.confidence_score) as avg_confidence,
    MAX(p.created_at) as last_prediction_date
FROM users u
LEFT JOIN predictions p ON u.id = p.user_id
GROUP BY u.id, u.username, u.email;

-- 授权给应用用户
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON predictions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON matches TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON teams TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON leagues TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_logs TO postgres;

GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT SELECT ON match_predictions TO postgres;
GRANT SELECT ON user_statistics TO postgres;

-- 创建存储过程用于用户注册
CREATE OR REPLACE FUNCTION register_user(
    p_username VARCHAR(50),
    p_email VARCHAR(100),
    p_hashed_password VARCHAR(255),
    p_role VARCHAR(20) DEFAULT 'user'
) RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    INSERT INTO users (username, email, hashed_password, role)
    VALUES (p_username, p_email, p_hashed_password, p_role)
    RETURNING id INTO user_id;

    -- 记录审计日志
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
    VALUES (user_id, 'USER_REGISTERED', 'user', user_id,
            json_build_object('username', p_username, 'email', p_email));

    RETURN user_id;
END;
$$ LANGUAGE plpgsql;

-- 创建存储过程用于创建预测
CREATE OR REPLACE FUNCTION create_prediction(
    p_user_id INTEGER,
    p_match_id INTEGER,
    p_prediction_data JSONB,
    p_confidence_score FLOAT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    prediction_id INTEGER;
BEGIN
    INSERT INTO predictions (user_id, match_id, prediction_data, confidence_score)
    VALUES (p_user_id, p_match_id, p_prediction_data, p_confidence_score)
    RETURNING id INTO prediction_id;

    -- 记录审计日志
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
    VALUES (p_user_id, 'PREDICTION_CREATED', 'prediction', prediction_id,
            json_build_object('match_id', p_match_id, 'confidence', p_confidence_score));

    RETURN prediction_id;
END;
$$ LANGUAGE plpgsql;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成';
    RAISE NOTICE '- 创建了基础表结构';
    RAISE NOTICE '- 插入了示例数据';
    RAISE NOTICE '- 创建了索引和视图';
    RAISE NOTICE '- 设置了存储过程';
END $$;