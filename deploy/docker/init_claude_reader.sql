-- ============================================
-- PostgreSQL 只读用户配置 (Claude Reader)
-- ============================================
-- 用途: MCP PostgreSQL 连接，仅允许 SELECT
-- 创建时间: 2026-02-27
-- ============================================

-- 1. 创建只读用户
CREATE USER claude_reader WITH PASSWORD 'claude_readonly_2026';

-- 2. 授予连接权限
GRANT CONNECT ON DATABASE football_db TO claude_reader;

-- 3. 切换到目标数据库后执行
-- \c football_db

-- 4. 授予 public schema 使用权限
GRANT USAGE ON SCHEMA public TO claude_reader;

-- 5. 授予所有现有表的只读权限
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_reader;

-- 6. 授予所有现有序列的只读权限 (某些查询可能需要)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO claude_reader;

-- 7. 设置默认权限 (未来创建的表自动授予只读权限)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO claude_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO claude_reader;

-- 8. 验证权限
-- \du claude_reader
-- SELECT * FROM information_schema.role_table_grants WHERE grantee = 'claude_reader';

-- ============================================
-- 撤销命令 (如需删除用户)
-- ============================================
-- REVOKE ALL PRIVILEGES ON DATABASE football_db FROM claude_reader;
-- REVOKE ALL PRIVILEGES ON SCHEMA public FROM claude_reader;
-- REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM claude_reader;
-- DROP USER claude_reader;
