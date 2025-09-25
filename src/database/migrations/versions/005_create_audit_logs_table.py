"""
from datetime import datetime, timezone
增强权限审计功能 - 创建audit_logs表

创建新的权限审计日志表，支持详细的操作记录和合规要求。
扩展原有的permission_audit_log功能，提供更全面的审计能力。

迁移ID: 005
创建时间: 2025-09-12
"""

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# 版本标识
revision = "005"
down_revision = "004_configure_permissions"
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库架构 - 创建audit_logs表"""

    # 创建审计日志表
    op.create_table(
        "audit_logs",
        # 主键
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, comment="审计日志ID"
        ),
        # 用户信息
        sa.Column(
            "user_id", sa.String(length=100), nullable=False, comment="操作用户ID"
        ),
        sa.Column(
            "username", sa.String(length=100), nullable=True, comment="操作用户名"
        ),
        sa.Column("user_role", sa.String(length=50), nullable=True, comment="用户角色"),
        sa.Column("session_id", sa.String(length=100), nullable=True, comment="会话ID"),
        # 操作信息
        sa.Column("action", sa.String(length=50), nullable=False, comment="操作类型"),
        sa.Column(
            "severity",
            sa.String(length=20),
            nullable=False,
            server_default="MEDIUM",
            comment="严重级别",
        ),
        sa.Column(
            "table_name", sa.String(length=100), nullable=True, comment="目标表名"
        ),
        sa.Column(
            "column_name", sa.String(length=100), nullable=True, comment="目标列名"
        ),
        sa.Column("record_id", sa.String(length=100), nullable=True, comment="记录ID"),
        # 数据变更信息
        sa.Column("old_value", sa.Text(), nullable=True, comment="操作前值"),
        sa.Column("new_value", sa.Text(), nullable=True, comment="操作后值"),
        sa.Column(
            "old_value_hash",
            sa.String(length=64),
            nullable=True,
            comment="旧值哈希（敏感数据）",
        ),
        sa.Column(
            "new_value_hash",
            sa.String(length=64),
            nullable=True,
            comment="新值哈希（敏感数据）",
        ),
        # 上下文信息
        sa.Column(
            "ip_address", sa.String(length=45), nullable=True, comment="客户端IP地址"
        ),
        sa.Column("user_agent", sa.Text(), nullable=True, comment="用户代理"),
        sa.Column(
            "request_path", sa.String(length=500), nullable=True, comment="请求路径"
        ),
        sa.Column(
            "request_method", sa.String(length=10), nullable=True, comment="HTTP方法"
        ),
        # 操作结果
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="操作是否成功",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        # 时间信息
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="操作时间戳",
        ),
        sa.Column(
            "duration_ms", sa.Integer(), nullable=True, comment="操作耗时（毫秒）"
        ),
        # 扩展信息
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="扩展元数据",
        ),
        sa.Column(
            "tags", sa.String(length=500), nullable=True, comment="标签（逗号分隔）"
        ),
        # 合规相关
        sa.Column(
            "compliance_category",
            sa.String(length=100),
            nullable=True,
            comment="合规分类",
        ),
        sa.Column(
            "retention_period_days",
            sa.Integer(),
            nullable=True,
            server_default="2555",
            comment="保留期限（天）",
        ),  # 7年
        sa.Column(
            "is_sensitive",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="是否包含敏感数据",
        ),
        # 继承BaseModel的字段
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            comment="更新时间",
        ),
        # 主键约束
        sa.PrimaryKeyConstraint("id"),
        # 表注释
        comment="权限审计日志表，记录所有敏感操作的详细信息",
    )

    # 创建索引以优化查询性能
    with op.batch_alter_table("audit_logs") as batch_op:
        # 用户和时间复合索引 - 用于按用户查询历史操作
        batch_op.create_index("idx_audit_user_timestamp", ["user_id", "timestamp"])

        # 表名和操作类型复合索引 - 用于按表查询操作
        batch_op.create_index("idx_audit_table_action", ["table_name", "action"])

        # 时间戳索引 - 用于时间范围查询
        batch_op.create_index("idx_audit_timestamp", ["timestamp"])

        # 严重级别索引 - 用于查询高风险操作
        batch_op.create_index("idx_audit_severity", ["severity"])

        # 操作成功状态索引 - 用于查询失败操作
        batch_op.create_index("idx_audit_success", ["success"])

        # 敏感数据标记索引 - 用于合规查询
        batch_op.create_index("idx_audit_sensitive", ["is_sensitive"])

        # 合规分类索引 - 用于合规报告
        batch_op.create_index("idx_audit_compliance", ["compliance_category"])

    # 为audit_logs表设置权限
    # 检查是否在离线模式
    if not context.is_offline_mode():
        connection = op.get_bind()

        # 为只读用户授予查询权限
        connection.execute(text("GRANT SELECT ON audit_logs TO football_reader;"))

        # 为写入用户授予查询和插入权限（审计日志通常只允许插入，不允许修改）
        connection.execute(
            text("GRANT SELECT, INSERT ON audit_logs TO football_writer;")
        )

        # 为管理员用户授予所有权限（包括删除权限，用于数据清理）
        connection.execute(
            text("GRANT ALL PRIVILEGES ON audit_logs TO football_admin;")
        )

        # 为序列授予使用权限
        connection.execute(
            text(
                "GRANT USAGE ON SEQUENCE audit_logs_id_seq TO football_writer, football_admin;"
            )
        )

        # 创建审计日志清理函数（用于定期清理过期日志）
        connection.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION cleanup_expired_audit_logs()
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
        BEGIN
            -- 删除超过保留期限的审计日志
            WITH deleted AS (
                DELETE FROM audit_logs
                WHERE timestamp < NOW() - INTERVAL '1 day' * retention_period_days
                RETURNING id
            )
            SELECT COUNT(*) INTO deleted_count FROM deleted;

            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """
            )
        )

        # 为清理函数授予执行权限
        connection.execute(
            text(
                "GRANT EXECUTE ON FUNCTION cleanup_expired_audit_logs() TO football_admin;"
            )
        )

        # 记录迁移日志到原有的权限审计表（如果存在）
        try:
            connection.execute(
                text(
                    """
            INSERT INTO permission_audit_log (username, action, table_name, privilege_type, granted, granted_by, notes)
            VALUES ('system', 'CREATE_TABLE', 'audit_logs', 'DDL', true, 'migration_005',
                   '创建增强的权限审计日志表，支持详细的操作记录和合规要求');
        """
                )
            )
        except Exception as e:
            # 如果permission_audit_log表不存在，忽略错误但记录日志
            print(f"Warning: Could not drop permission_audit_log table: {e}")
    else:
        # 离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped audit_logs permission grants")
        op.execute("-- offline mode: skipped audit_logs cleanup function creation")
        op.execute("-- offline mode: skipped audit_logs function execution grants")


def downgrade():
    """降级数据库架构 - 删除audit_logs表"""

    # 检查是否在离线模式
    if not context.is_offline_mode():
        connection = op.get_bind()

        # 记录回滚日志
        try:
            connection.execute(
                text(
                    """
                INSERT INTO permission_audit_log (username, action, table_name, privilege_type, granted, granted_by, notes)
                VALUES ('system', 'DROP_TABLE', 'audit_logs', 'DDL', false, 'migration_005_downgrade',
                       '回滚：删除增强的权限审计日志表');
            """
                )
            )
        except Exception as e:
            # 如果permission_audit_log表不存在，忽略错误但记录日志
            print(f"Warning: Could not drop permission_audit_log table: {e}")

        # 删除清理函数
        connection.execute(
            text("DROP FUNCTION IF EXISTS cleanup_expired_audit_logs();")
        )
    else:
        # 离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped audit_logs cleanup function deletion")
        op.execute("-- offline mode: skipped audit_logs rollback logging")

    # 删除索引（会随表一起删除，但为了明确性仍然列出）
    # 索引会随着表的删除自动删除

    # 删除audit_logs表
    op.drop_table("audit_logs")
