"""配置数据库权限

配置三类数据库用户的权限：
- football_reader: 只读用户（分析、前端）
- football_writer: 写入用户（数据采集）
- football_admin: 管理员用户（运维、迁移）

基于 DATA_DESIGN.md 第5.3节设计。

Revision ID: 004_configure_permissions
Revises: f48d412852cc
Create Date: 2025-09-10 16:40:00.000000
"""

import os

from alembic import context, op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_REVISION_21")
down_revision = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_DOWN_REVISION_2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """配置数据库权限"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过数据库权限配置")
        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped database user creation")
        op.execute("-- offline mode: skipped database permission configuration")
        return

    # 获取数据库连接
    connection = op.get_bind()

    # 获取当前数据库名称（支持测试环境）
    db_name = os.getenv("TEST_DB_NAME", "football_prediction")
    if os.getenv("ENVIRONMENT") == "test":
        db_name = os.getenv("TEST_DB_NAME", "football_prediction_test")

    # =============================================================================
    # 创建数据库用户
    # =============================================================================

    # 创建只读用户（分析、前端）
    connection.execute(
        text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_54")) THEN
                CREATE USER football_reader WITH PASSWORD 'reader_password_2025';
            END IF;
        END
        $$;
    """
        )
    )

    # 创建写入用户（数据采集）
    connection.execute(
        text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_66")) THEN
                CREATE USER football_writer WITH PASSWORD 'writer_password_2025';
            END IF;
        END
        $$;
    """
        )
    )

    # 创建管理员用户（运维、迁移）
    connection.execute(
        text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_78")) THEN
                CREATE USER football_admin WITH PASSWORD 'admin_password_2025';
            END IF;
        END
        $$;
    """
        )
    )

    # =============================================================================
    # 配置只读用户权限
    # =============================================================================

    # 授予连接数据库的权限
    connection.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO football_reader;"))

    # 授予使用public schema的权限
    connection.execute(text("GRANT USAGE ON SCHEMA public TO football_reader;"))

    # 授予所有表的SELECT权限
    connection.execute(
        text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_reader;")
    )

    # 授予所有序列的SELECT权限
    connection.execute(
        text("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO football_reader;")
    )

    # 为未来创建的表自动授予SELECT权限
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO football_reader;"
        )
    )

    # 为未来创建的序列自动授予SELECT权限
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO football_reader;"
        )
    )

    # =============================================================================
    # 配置写入用户权限
    # =============================================================================

    # 授予连接数据库的权限
    connection.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO football_writer;"))

    # 授予使用public schema的权限
    connection.execute(text("GRANT USAGE ON SCHEMA public TO football_writer;"))

    # 授予所有表的SELECT, INSERT, UPDATE权限
    connection.execute(
        text(
            "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO football_writer;"
        )
    )

    # 授予所有序列的SELECT, USAGE权限
    connection.execute(
        text(
            "GRANT SELECT, USAGE ON ALL SEQUENCES IN SCHEMA public TO football_writer;"
        )
    )

    # 为未来创建的表自动授予权限
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO football_writer;"
        )
    )

    # 为未来创建的序列自动授予权限
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, USAGE ON SEQUENCES TO football_writer;"
        )
    )

    # 特殊权限：允许删除采集日志和原始数据（用于清理）
    tables_with_delete_permission = [
        "data_collection_logs",
        "raw_match_data",
        "raw_odds_data",
    ]

    for table in tables_with_delete_permission:
        connection.execute(text(f"GRANT DELETE ON {table} TO football_writer;"))

    # =============================================================================
    # 配置管理员用户权限
    # =============================================================================

    # 授予连接数据库的权限
    connection.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO football_admin;"))

    # 授予所有权限
    connection.execute(
        text(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO football_admin;")
    )

    # 授予所有表的所有权限
    connection.execute(
        text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO football_admin;")
    )

    # 授予所有序列的所有权限
    connection.execute(
        text(
            "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO football_admin;"
        )
    )

    # 授予所有函数的执行权限
    connection.execute(
        text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO football_admin;")
    )

    # 为未来创建的对象自动授予权限
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO football_admin;"
        )
    )
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO football_admin;"
        )
    )
    connection.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO football_admin;"
        )
    )

    # 授予创建schema的权限
    connection.execute(text(f"GRANT CREATE ON DATABASE {db_name} TO football_admin;"))

    # =============================================================================
    # 创建角色和权限视图
    # =============================================================================

    # 创建权限查询视图，方便监控用户权限
    connection.execute(
        text(
            """
        CREATE OR REPLACE VIEW user_permissions AS
        SELECT
            u.usename as username,
            d.datname as database,
            CASE
                WHEN u.usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_54") THEN 'READ_only'
                WHEN u.usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_66") THEN 'read_write'
                WHEN u.usename = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_USENAME_78") THEN 'admin'
                ELSE 'unknown'
            END as role_type,
            u.usecreatedb as can_create_db,
            u.usesuper as is_superuser,
            u.valuntil as password_expiry
        FROM pg_user u
        CROSS JOIN pg_database d
        WHERE d.datname = current_database()
        AND u.usename IN ('football_reader', 'football_writer', 'football_admin');
    """
        )
    )

    # 创建表权限查询视图
    connection.execute(
        text(
            """
        CREATE OR REPLACE VIEW table_permissions AS
        SELECT
            grantee,
            table_name,
            privilege_type,
            is_grantable
        FROM information_schema.table_privileges
        WHERE grantee IN ('football_reader', 'football_writer', 'football_admin')
        AND table_schema = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_25")
        ORDER BY grantee, table_name, privilege_type;
    """
        )
    )

    # =============================================================================
    # 创建权限管理函数
    # =============================================================================

    # 创建检查用户权限的函数
    connection.execute(
        text(
            """
        CREATE OR REPLACE FUNCTION check_user_permissions(username TEXT)
        RETURNS TABLE(
            table_name TEXT,
            select_perm BOOLEAN,
            insert_perm BOOLEAN,
            update_perm BOOLEAN,
            delete_perm BOOLEAN
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                t.table_name::TEXT,
                bool_or(tp.privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")) as select_perm,
                bool_or(tp.privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")) as insert_perm,
                bool_or(tp.privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")) as update_perm,
                bool_or(tp.privilege_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_PRIVILEGE_TYPE_")) as delete_perm
            FROM information_schema.tables t
            LEFT JOIN information_schema.table_privileges tp
                ON t.table_name = tp.table_name
                AND tp.grantee = username
            WHERE t.table_schema = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_SCHEMA_25")
            AND t.table_type = os.getenv("004_CONFIGURE_DATABASE_PERMISSIONS_TABLE_TYPE_294")
            GROUP BY t.table_name
            ORDER BY t.table_name;
        END;
        $$ LANGUAGE plpgsql;
    """
        )
    )

    # 创建权限审计日志表
    connection.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS permission_audit_log (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL,
            table_name VARCHAR(100),
            privilege_type VARCHAR(20),
            granted BOOLEAN NOT NULL,
            granted_by VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
    """
        )
    )

    # 为权限审计日志表授予权限
    connection.execute(text("GRANT SELECT ON permission_audit_log TO football_reader;"))
    connection.execute(
        text("GRANT SELECT, INSERT ON permission_audit_log TO football_writer;")
    )
    connection.execute(
        text("GRANT ALL PRIVILEGES ON permission_audit_log TO football_admin;")
    )
    connection.execute(
        text(
            "GRANT USAGE ON SEQUENCE permission_audit_log_id_seq TO football_writer, football_admin;"
        )
    )

    # =============================================================================
    # 记录权限配置日志
    # =============================================================================

    connection.execute(
        text(
            """
        INSERT INTO permission_audit_log (username, action, privilege_type, granted, granted_by, notes)
        VALUES
        ('football_reader', 'INITIAL_SETUP', 'SELECT', true, 'migration_004', '初始化只读用户权限'),
        ('football_writer', 'INITIAL_SETUP', 'SELECT,INSERT,UPDATE', true, 'migration_004', '初始化读写用户权限'),
        ('football_admin', 'INITIAL_SETUP', 'ALL', true, 'migration_004', '初始化管理员用户权限');
    """
        )
    )


def downgrade() -> None:
    """回滚数据库权限配置"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过数据库权限回滚")
        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped database permission rollback")
        op.execute("-- offline mode: skipped database user deletion")
        return

    # 获取数据库连接
    connection = op.get_bind()

    # 获取当前数据库名称（支持测试环境）
    db_name = os.getenv("TEST_DB_NAME", "football_prediction")
    if os.getenv("ENVIRONMENT") == "test":
        db_name = os.getenv("TEST_DB_NAME", "football_prediction_test")

    # 删除权限管理相关对象
    connection.execute(text("DROP VIEW IF EXISTS user_permissions;"))
    connection.execute(text("DROP VIEW IF EXISTS table_permissions;"))
    connection.execute(text("DROP FUNCTION IF EXISTS check_user_permissions(TEXT);"))
    connection.execute(text("DROP TABLE IF EXISTS permission_audit_log;"))

    # 撤销用户权限
    connection.execute(
        text(f"REVOKE ALL PRIVILEGES ON DATABASE {db_name} FROM football_reader;")
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM football_reader;"
        )
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM football_reader;"
        )
    )

    connection.execute(
        text(f"REVOKE ALL PRIVILEGES ON DATABASE {db_name} FROM football_writer;")
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM football_writer;"
        )
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM football_writer;"
        )
    )

    connection.execute(
        text(f"REVOKE ALL PRIVILEGES ON DATABASE {db_name} FROM football_admin;")
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM football_admin;"
        )
    )
    connection.execute(
        text(
            "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM football_admin;"
        )
    )

    # 删除用户（注意：在生产环境中可能不希望删除用户）
    connection.execute(text("DROP USER IF EXISTS football_reader;"))
    connection.execute(text("DROP USER IF EXISTS football_writer;"))
    connection.execute(text("DROP USER IF EXISTS football_admin;"))
