-- 测试数据库初始化脚本
-- 创建测试表和基础数据

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 创建测试用模式
CREATE SCHEMA IF NOT EXISTS test_schema;

-- 设置搜索路径
SET search_path TO public, test_schema;

-- 创建索引以提高测试性能
CREATE INDEX IF NOT EXISTS idx_test_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_test_teams_name ON teams(name);
CREATE INDEX IF NOT EXISTS idx_test_predictions_match_id ON predictions(match_id);

-- 插入基础测试数据
INSERT INTO teams (id, name, short_name, country, founded) VALUES
  (1, 'Test Team A', 'TTA', 'Test Country', 2020),
  (2, 'Test Team B', 'TTB', 'Test Country', 2021)
ON CONFLICT (id) DO NOTHING;

INSERT INTO leagues (id, name, country, season) VALUES
  (1, 'Test League', 'Test Country', 2024)
ON CONFLICT (id) DO NOTHING;

-- 创建测试用户和权限（如果需要）
DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'test_user') THEN
    CREATE ROLE test_user WITH LOGIN PASSWORD 'test_password';
  END IF;
END
$$;

-- 授予必要权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_user;
GRANT ALL PRIVILEGES ON SCHEMA test_schema TO test_user;

-- 设置测试环境参数
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 记录慢查询

COMMIT;
