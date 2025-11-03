-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建基础表结构（如果Alembic未运行）
-- 这里可以放置基础数据插入语句

-- 插入示例数据（仅开发环境）
INSERT INTO users (id, username, email, hashed_password, is_active, created_at, updated_at)
VALUES
    (uuid_generate_v4(), 'admin', 'admin@footballprediction.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LFvO', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- 创建示例预测数据（开发环境）
INSERT INTO predictions (id, match_id, user_id, prediction, confidence, created_at, updated_at)
VALUES
    (uuid_generate_v4(), 1, (SELECT id FROM users WHERE username = 'admin' LIMIT 1), 'home_win', 75, NOW(), NOW())
ON CONFLICT DO NOTHING;
