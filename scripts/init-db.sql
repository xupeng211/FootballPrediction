-- 足球预测系统数据库初始化脚本
-- 创建数据库用户和基础配置

-- 如果用户不存在，创建用户（在Docker中已经创建，这里仅作备用）
DO
$$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles
        WHERE  rolname = 'football_user'
    ) THEN
        CREATE USER football_user WITH PASSWORD 'football_pass';
    END IF;
END
$$;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE football_prediction_dev TO football_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO football_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO football_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO football_user;

-- 设置默认权限（未来创建的对象）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO football_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO football_user;

-- 创建PostgreSQL扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- 创建自定义函数或存储过程（如果需要）
-- 这里可以添加业务相关的数据库函数
