"""Add roles column to users table

Revision ID: add_user_roles_column
Revises:
Create Date: 2025-10-13 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_user_roles_column"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """添加roles列到users表"""
    # 添加roles列
    op.add_column(
        "users",
        sa.Column(
            "roles",
            sa.Text(),
            nullable=True,
            server_default="user",
            comment="用户角色，逗号分隔",
        ),
    )

    # 为现有用户设置默认角色
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        UPDATE users
        SET roles = CASE
            WHEN is_admin = true THEN 'admin'
            WHEN is_analyst = true THEN 'analyst'
            ELSE 'user'
        END
        WHERE roles IS NULL
    """
        )
    )

    # 将列设置为非空
    op.alter_column("users", "roles", nullable=False)


def downgrade():
    """移除roles列"""
    op.drop_column("users", "roles")
