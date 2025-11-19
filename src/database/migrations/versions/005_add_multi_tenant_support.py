from typing import Optional

"""添加多租户支持
Add Multi-Tenant Support.

Revision ID: 005_add_multi_tenant_support
Revises: 004_configure_database_permissions
Create Date: 2025-10-30 16:53:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "005_add_multi_tenant_support"
down_revision: str | None = "004_configure_database_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级数据库,添加多租户支持."""
    # 创建租户表
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="租户名称"),
        sa.Column("slug", sa.String(length=50), nullable=False, comment="租户标识符"),
        sa.Column("domain", sa.String(length=255), nullable=True, comment="自定义域名"),
        sa.Column("description", sa.Text(), nullable=True, comment="租户描述"),
        sa.Column(
            "contact_email", sa.String(length=255), nullable=False, comment="联系邮箱"
        ),
        sa.Column(
            "contact_phone", sa.String(length=50), nullable=True, comment="联系电话"
        ),
        sa.Column(
            "company_name", sa.String(length=100), nullable=True, comment="公司名称"
        ),
        sa.Column("company_address", sa.Text(), nullable=True, comment="公司地址"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="租户状态"),
        sa.Column("plan", sa.String(length=20), nullable=False, comment="租户计划"),
        sa.Column("max_users", sa.Integer(), nullable=False, comment="最大用户数"),
        sa.Column(
            "max_predictions_per_day",
            sa.Integer(),
            nullable=False,
            comment="每日最大预测数",
        ),
        sa.Column(
            "max_api_calls_per_hour",
            sa.Integer(),
            nullable=False,
            comment="每小时最大API调用数",
        ),
        sa.Column(
            "storage_quota_mb", sa.Integer(), nullable=False, comment="存储配额(MB)"
        ),
        sa.Column(
            "trial_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="试用结束时间",
        ),
        sa.Column(
            "subscription_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="订阅结束时间",
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="租户设置",
        ),
        sa.Column(
            "features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="启用的功能",
        ),
        sa.Column(
            "branding",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="品牌定制",
        ),
        sa.Column(
            "statistics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="租户统计",
        ),
        sa.Column(
            "usage_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="使用指标",
        ),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建者ID"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", name="uq_tenant_domain"),
        sa.UniqueConstraint("slug", name="uq_tenant_slug"),
        comment="租户表",
    )

    # 创建租户索引
    op.create_index(
        "idx_tenant_status_plan", "tenants", ["status", "plan"], unique=False
    )
    op.create_index(
        "idx_tenant_subscription", "tenants", ["subscription_ends_at"], unique=False
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_name"), "tenants", ["name"], unique=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    # 创建租户权限表
    op.create_table(
        "tenant_permissions",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="权限名称"),
        sa.Column("code", sa.String(length=50), nullable=False, comment="权限代码"),
        sa.Column("description", sa.Text(), nullable=True, comment="权限描述"),
        sa.Column("scope", sa.String(length=20), nullable=False, comment="权限范围"),
        sa.Column(
            "resource_type", sa.String(length=50), nullable=True, comment="资源类型"
        ),
        sa.Column(
            "resource_id", sa.String(length=100), nullable=True, comment="资源ID"
        ),
        sa.Column(
            "actions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="允许的动作列表",
        ),
        sa.Column(
            "conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="权限条件",
        ),
        sa.Column(
            "restrictions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="权限限制",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_tenant_permission"),
        comment="租户权限表",
    )

    # 创建租户权限索引
    op.create_index(
        "idx_tenant_permission_resource",
        "tenant_permissions",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index(
        "idx_tenant_permission_scope",
        "tenant_permissions",
        ["tenant_id", "scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_permissions_id"), "tenant_permissions", ["id"], unique=False
    )

    # 创建租户角色表
    op.create_table(
        "tenant_roles",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="角色名称"),
        sa.Column("code", sa.String(length=50), nullable=False, comment="角色代码"),
        sa.Column("description", sa.Text(), nullable=True, comment="角色描述"),
        sa.Column("level", sa.Integer(), nullable=False, comment="角色级别"),
        sa.Column(
            "is_system_role", sa.Boolean(), nullable=False, comment="是否为系统角色"
        ),
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="权限列表",
        ),
        sa.Column(
            "restrictions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="角色限制",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_tenant_role"),
        comment="租户角色表",
    )

    # 创建租户角色索引
    op.create_index(
        "idx_tenant_role_level", "tenant_roles", ["tenant_id", "level"], unique=False
    )
    op.create_index(op.f("ix_tenant_roles_id"), "tenant_roles", ["id"], unique=False)

    # 创建角色权限关联表
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("role_id", sa.Integer(), nullable=False, comment="角色ID"),
        sa.Column("permission_id", sa.Integer(), nullable=False, comment="权限ID"),
        sa.Column("granted_by", sa.Integer(), nullable=True, comment="授权者ID"),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), nullable=False, comment="授权时间"
        ),
        sa.Column(
            "conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="特殊条件",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["tenant_permissions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["tenant_roles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        comment="角色权限关联表",
    )

    # 创建角色权限关联索引
    op.create_index(
        "idx_role_permission_granted", "role_permissions", ["granted_at"], unique=False
    )
    op.create_index(
        op.f("ix_role_permissions_id"), "role_permissions", ["id"], unique=False
    )

    # 创建用户角色分配表
    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("role_id", sa.Integer(), nullable=False, comment="角色ID"),
        sa.Column("assigned_by", sa.Integer(), nullable=True, comment="分配者ID"),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="分配时间",
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True, comment="过期时间"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否激活"),
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["tenant_roles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tenant_id", "role_id", name="uq_user_tenant_role"
        ),
        comment="用户角色分配表",
    )

    # 创建用户角色分配索引
    op.create_index(
        "idx_role_assignment_expiry",
        "user_role_assignments",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_user_role_assignment",
        "user_role_assignments",
        ["user_id", "tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_role_assignments_id"),
        "user_role_assignments",
        ["id"],
        unique=False,
    )

    # 为用户表添加租户关联字段
    op.add_column(
        "users",
        sa.Column("tenant_id", sa.Integer(), nullable=True, comment="所属租户ID"),
    )
    op.create_foreign_key(
        "fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"]
    )
    op.create_index("idx_users_tenant_id", "users", ["tenant_id"], unique=False)

    # 为主要业务表添加租户ID字段,实现数据隔离
    # 预测表
    op.add_column(
        "predictions",
        sa.Column("tenant_id", sa.Integer(), nullable=True, comment="所属租户ID"),
    )
    op.create_foreign_key(
        "fk_predictions_tenant_id", "predictions", "tenants", ["tenant_id"], ["id"]
    )
    op.create_index(
        "idx_predictions_tenant_id", "predictions", ["tenant_id"], unique=False
    )

    # 比赛表
    op.add_column(
        "matches",
        sa.Column("tenant_id", sa.Integer(), nullable=True, comment="所属租户ID"),
    )
    op.create_foreign_key(
        "fk_matches_tenant_id", "matches", "tenants", ["tenant_id"], ["id"]
    )
    op.create_index("idx_matches_tenant_id", "matches", ["tenant_id"], unique=False)

    # 创建默认租户
    op.execute(
        """
        INSERT INTO tenants (name,
    slug,
    contact_email,
    status,
    plan,
    max_users,
    max_predictions_per_day,
    max_api_calls_per_hour,
    storage_quota_mb,
    is_active,
    created_at,
    updated_at)
        VALUES (
            '默认租户',
            'default',
            'admin@example.com',
            'active',
            'enterprise',
            1000,
            100000,
            1000000,
            100000,
            true,
            NOW(),
            NOW()
        )
    """
    )

    # 为现有用户分配到默认租户
    op.execute(
        """
        UPDATE users SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL
    """
    )

    # 为现有预测数据分配到默认租户
    op.execute(
        """
        UPDATE predictions SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL
    """
    )

    # 为现有比赛数据分配到默认租户
    op.execute(
        """
        UPDATE matches SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL
    """
    )


def downgrade() -> None:
    """降级数据库,移除多租户支持."""
    # 删除索引
    op.drop_index("idx_users_tenant_id", table_name="users")
    op.drop_index("idx_predictions_tenant_id", table_name="predictions")
    op.drop_index("idx_matches_tenant_id", table_name="matches")
    op.drop_index("idx_role_assignment_expiry", table_name="user_role_assignments")
    op.drop_index("idx_user_role_assignment", table_name="user_role_assignments")
    op.drop_index("idx_role_permission_granted", table_name="role_permissions")
    op.drop_index("idx_tenant_role_level", table_name="tenant_roles")
    op.drop_index("idx_tenant_permission_resource", table_name="tenant_permissions")
    op.drop_index("idx_tenant_permission_scope", table_name="tenant_permissions")
    op.drop_index("idx_tenant_subscription", table_name="tenants")
    op.drop_index("idx_tenant_status_plan", table_name="tenants")

    # 删除外键约束
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_constraint("fk_predictions_tenant_id", "predictions", type_="foreignkey")
    op.drop_constraint("fk_matches_tenant_id", "matches", type_="foreignkey")

    # 删除租户相关字段
    op.drop_column("matches", "tenant_id")
    op.drop_column("predictions", "tenant_id")
    op.drop_column("users", "tenant_id")

    # 删除表
    op.drop_table("user_role_assignments")
    op.drop_table("role_permissions")
    op.drop_table("tenant_roles")
    op.drop_table("tenant_permissions")
    op.drop_table("tenants")
