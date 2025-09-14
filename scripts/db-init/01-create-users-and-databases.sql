-- 数据库初始化脚本
-- 创建应用所需的用户、数据库和权限配置
-- 支持读写分离的多用户架构

-- 设置客户端编码
SET client_encoding = 'UTF8';

-- 创建应用数据库
CREATE DATABASE football_prediction_dev
    WITH ENCODING 'UTF8'
    LC_COLLATE='C'
    LC_CTYPE='C'
    TEMPLATE=template0;

-- 创建测试数据库
CREATE DATABASE football_prediction_test
    WITH ENCODING 'UTF8'
    LC_COLLATE='C'
    LC_CTYPE='C'
    TEMPLATE=template0;

-- 连接到应用数据库进行后续配置
\c football_prediction_dev;

-- 启用必要的PostgreSQL扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- 创建应用专用用户
CREATE USER football_user WITH PASSWORD 'football_pass';
COMMENT ON ROLE football_user IS '足球预测应用主用户';

-- 创建读者用户（只读权限）
CREATE USER football_reader WITH PASSWORD 'reader_pass';
COMMENT ON ROLE football_reader IS '只读用户，用于数据分析和前端查询';

-- 创建写入用户（数据采集专用）
CREATE USER football_writer WITH PASSWORD 'writer_pass';
COMMENT ON ROLE football_writer IS '写入用户，专用于数据采集任务';

-- 创建管理员用户
CREATE USER football_admin WITH PASSWORD 'admin_pass';
COMMENT ON ROLE football_admin IS '管理员用户，用于运维和数据库管理';

-- 为管理员用户添加数据库创建权限
ALTER USER football_admin CREATEDB;

-- 授权主用户对数据库的所有权限
GRANT ALL PRIVILEGES ON DATABASE football_prediction_dev TO football_user;
GRANT ALL PRIVILEGES ON DATABASE football_prediction_test TO football_user;

-- 确保用户可以创建schema
GRANT CREATE ON DATABASE football_prediction_dev TO football_user;
GRANT CREATE ON DATABASE football_prediction_test TO football_user;

-- 为管理员用户授权
GRANT ALL PRIVILEGES ON DATABASE football_prediction_dev TO football_admin;
GRANT ALL PRIVILEGES ON DATABASE football_prediction_test TO football_admin;
