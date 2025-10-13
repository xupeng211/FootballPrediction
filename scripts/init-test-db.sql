-- 测试数据库初始化脚本
-- 用于集成测试和 E2E 测试

-- 创建测试用户
CREATE USER IF NOT EXISTS test_user WITH PASSWORD 'test_pass';
ALTER USER test_user CREATEDB;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE football_test TO test_user;
GRANT ALL ON SCHEMA public TO test_user;

-- 创建测试模式（如果需要）
CREATE SCHEMA IF NOT EXISTS test_schema;
GRANT ALL ON SCHEMA test_schema TO test_user;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 设置配置
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 100;
SELECT pg_reload_conf();

-- 创建测试表（如果不存在）
CREATE TABLE IF NOT EXISTS test_data (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入测试数据
INSERT INTO test_data (test_name) VALUES
    ('integration_test'),
    ('e2e_test')
ON CONFLICT DO NOTHING;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_test_data_created_at ON test_data(created_at);

-- 创建测试视图
CREATE OR REPLACE VIEW test_summary AS
SELECT
    COUNT(*) as total_tests,
    COUNT(CASE WHEN test_name LIKE '%integration%' THEN 1 END) as integration_tests,
    COUNT(CASE WHEN test_name LIKE '%e2e%' THEN 1 END) as e2e_tests,
    MAX(created_at) as last_test_run
FROM test_data;

-- 创建测试函数
CREATE OR REPLACE FUNCTION cleanup_test_data()
RETURNS void AS $$
BEGIN
    DELETE FROM test_data WHERE created_at < NOW() - INTERVAL '7 days';
    RAISE NOTICE 'Cleaned up old test data';
END;
$$ LANGUAGE plpgsql;

-- 创建触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS update_test_data_updated_at ON test_data;
CREATE TRIGGER update_test_data_updated_at
    BEFORE UPDATE ON test_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 授权
GRANT SELECT, INSERT, UPDATE, DELETE ON test_data TO test_user;
GRANT SELECT ON test_summary TO test_user;
GRANT EXECUTE ON FUNCTION cleanup_test_data() TO test_user;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'Test database initialized successfully';
    RAISE NOTICE 'Test user: test_user';
    RAISE NOTICE 'Test schema: public, test_schema';
END $$;