-- 权限配置脚本 - 第二阶段
-- 在表创建后设置详细的表级权限
-- 本脚本将在表结构创建后执行

-- 连接到应用数据库
\c football_prediction_dev;

-- 创建自定义函数来批量设置权限
CREATE OR REPLACE FUNCTION setup_table_permissions() RETURNS void AS $$
DECLARE
    table_record RECORD;
BEGIN
    -- 遍历所有用户表（排除系统表）
    FOR table_record IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename NOT LIKE 'pg_%'
        AND tablename NOT LIKE 'information_schema%'
    LOOP
        -- 为主用户授予所有权限
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE %I TO football_user', table_record.tablename);

        -- 为管理员用户授予所有权限
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE %I TO football_admin', table_record.tablename);

        -- 为读者用户授予只读权限
        EXECUTE format('GRANT SELECT ON TABLE %I TO football_reader', table_record.tablename);

        -- 为写入用户设置权限（根据表类型）
        IF table_record.tablename LIKE 'raw_%' OR
           table_record.tablename LIKE '%_log%' OR
           table_record.tablename IN ('matches', 'odds', 'predictions') THEN
            -- 数据采集相关表：允许插入和更新
            EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE %I TO football_writer', table_record.tablename);
        ELSE
            -- 其他表：只读权限
            EXECUTE format('GRANT SELECT ON TABLE %I TO football_writer', table_record.tablename);
        END IF;

        RAISE NOTICE '已设置表 % 的权限', table_record.tablename;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 创建序列权限设置函数
CREATE OR REPLACE FUNCTION setup_sequence_permissions() RETURNS void AS $$
DECLARE
    seq_record RECORD;
BEGIN
    -- 遍历所有序列
    FOR seq_record IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'public'
    LOOP
        -- 为主用户和管理员授予序列使用权限
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO football_user', seq_record.sequence_name);
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO football_admin', seq_record.sequence_name);

        -- 为写入用户授予序列使用权限（用于插入数据）
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %I TO football_writer', seq_record.sequence_name);

        RAISE NOTICE '已设置序列 % 的权限', seq_record.sequence_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 设置schema级别的权限
GRANT USAGE ON SCHEMA public TO football_reader;
GRANT USAGE ON SCHEMA public TO football_writer;
GRANT ALL ON SCHEMA public TO football_user;
GRANT ALL ON SCHEMA public TO football_admin;

-- 为未来创建的表设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO football_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO football_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO football_reader;

-- 为未来创建的序列设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO football_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO football_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO football_writer;

-- 创建触发器函数，在新表创建后自动设置权限
CREATE OR REPLACE FUNCTION auto_grant_permissions()
RETURNS event_trigger AS $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() WHERE command_tag = 'CREATE TABLE'
    LOOP
        -- 为新创建的表自动设置权限
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE %s TO football_user', obj.object_identity);
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE %s TO football_admin', obj.object_identity);
        EXECUTE format('GRANT SELECT ON TABLE %s TO football_reader', obj.object_identity);

        -- 根据表名设置写入用户权限
        IF obj.object_identity ~ '.*\.raw_.*' OR
           obj.object_identity ~ '.*\.*_log.*' OR
           obj.object_identity ~ '.*(matches|odds|predictions)' THEN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE %s TO football_writer', obj.object_identity);
        ELSE
            EXECUTE format('GRANT SELECT ON TABLE %s TO football_writer', obj.object_identity);
        END IF;

        RAISE NOTICE '自动为新表 % 设置权限', obj.object_identity;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 创建事件触发器
DROP EVENT TRIGGER IF EXISTS auto_grant_trigger;
CREATE EVENT TRIGGER auto_grant_trigger ON ddl_command_end
WHEN TAG IN ('CREATE TABLE')
EXECUTE FUNCTION auto_grant_permissions();

-- 创建用于监控权限的视图
CREATE OR REPLACE VIEW user_table_permissions AS
SELECT
    schemaname,
    tablename,
    usename,
    has_table_privilege(usename, schemaname||'.'||tablename, 'SELECT') as can_select,
    has_table_privilege(usename, schemaname||'.'||tablename, 'INSERT') as can_insert,
    has_table_privilege(usename, schemaname||'.'||tablename, 'UPDATE') as can_update,
    has_table_privilege(usename, schemaname||'.'||tablename, 'DELETE') as can_delete
FROM pg_tables
CROSS JOIN pg_user
WHERE schemaname = 'public'
    AND usename IN ('football_user', 'football_reader', 'football_writer', 'football_admin')
ORDER BY tablename, usename;

-- 授权所有用户查看权限视图
GRANT SELECT ON user_table_permissions TO football_user, football_reader, football_writer, football_admin;

-- 输出设置完成信息
SELECT 'PostgreSQL权限配置脚本执行完成' as status;
