"""V105.0 多源数据表迁移 - metrics_multi_source_data

Revision ID: 002_v105
Revises: 001
Create Date: 2026-01-03 09:00:00.000000

此迁移创建 `metrics_multi_source_data` 表，用于存储多供应商赔率数据。
该表支持：
1. 多数据源共存（通过 match_id + source_name 唯一约束）
2. 开盘/终盘赔率分别存储
3. 完整性评分和验证元数据
4. 数据时间戳追踪
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_v105"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 metrics_multi_source_data 表及索引"""

    # 创建主表
    op.create_table(
        "metrics_multi_source_data",
        sa.Column("id", sa.BigInteger(), nullable=False, comment="主键ID"),
        sa.Column("match_id", sa.String(length=100), nullable=False, comment="比赛ID"),
        sa.Column(
            "source_name", sa.String(length=50), nullable=False, comment="数据源名称 (如: Entity_P)"
        ),
        # 开盘赔率（Opening Odds）
        sa.Column("init_h", sa.Float(), nullable=True, comment="初始主胜赔率"),
        sa.Column("init_d", sa.Float(), nullable=True, comment="初始平局赔率"),
        sa.Column("init_a", sa.Float(), nullable=True, comment="初始客胜赔率"),
        # 开盘时间
        sa.Column("init_time", sa.DateTime(), nullable=True, comment="开盘时间"),
        # 终盘赔率（Final Odds）
        sa.Column("final_h", sa.Float(), nullable=True, comment="最终主胜赔率"),
        sa.Column("final_d", sa.Float(), nullable=True, comment="最终平局赔率"),
        sa.Column("final_a", sa.Float(), nullable=True, comment="最终客胜赔率"),
        # 终盘时间
        sa.Column("final_time", sa.DateTime(), nullable=True, comment="终盘时间"),
        # 完整性评分和验证
        sa.Column(
            "integrity_score", sa.Float(), nullable=True, comment="完整性评分 (1/P1 + 1/P2 + 1/P3)"
        ),
        sa.Column("is_valid", sa.Boolean(), nullable=True, comment="是否通过验证"),
        sa.Column("validation_error", sa.Text(), nullable=True, comment="验证错误信息"),
        # 数据时间戳
        sa.Column("data_timestamp", sa.DateTime(), nullable=False, comment="数据时间戳"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="记录创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="记录更新时间",
        ),
        # 主键约束
        sa.PrimaryKeyConstraint("id", name="pk_metrics_multi_source_data"),
        # 唯一约束：同一比赛同一数据源只能有一条记录
        sa.UniqueConstraint(
            "match_id", "source_name", name="uq_metrics_multi_source_data_match_source"
        ),
        comment="多源赔率数据表 (V105.0)",
    )

    # 创建索引 - 提升查询性能
    op.create_index(
        "idx_metrics_multi_source_data_match_id",
        "metrics_multi_source_data",
        ["match_id"],
        unique=False,
    )

    op.create_index(
        "idx_metrics_multi_source_data_source_name",
        "metrics_multi_source_data",
        ["source_name"],
        unique=False,
    )

    op.create_index(
        "idx_metrics_multi_source_data_final_h",
        "metrics_multi_source_data",
        ["final_h"],
        unique=False,
    )

    op.create_index(
        "idx_metrics_multi_source_data_is_valid",
        "metrics_multi_source_data",
        ["is_valid"],
        unique=False,
    )

    op.create_index(
        "idx_metrics_multi_source_data_data_timestamp",
        "metrics_multi_source_data",
        ["data_timestamp"],
        unique=False,
    )

    # 创建复合索引用于常见查询
    op.create_index(
        "idx_metrics_multi_source_data_match_valid",
        "metrics_multi_source_data",
        ["match_id", "is_valid"],
        unique=False,
    )


def downgrade() -> None:
    """回滚：删除 metrics_multi_source_data 表"""

    # 删除索引
    op.drop_index(
        "idx_metrics_multi_source_data_match_valid", table_name="metrics_multi_source_data"
    )
    op.drop_index(
        "idx_metrics_multi_source_data_data_timestamp", table_name="metrics_multi_source_data"
    )
    op.drop_index("idx_metrics_multi_source_data_is_valid", table_name="metrics_multi_source_data")
    op.drop_index("idx_metrics_multi_source_data_final_h", table_name="metrics_multi_source_data")
    op.drop_index(
        "idx_metrics_multi_source_data_source_name", table_name="metrics_multi_source_data"
    )
    op.drop_index("idx_metrics_multi_source_data_match_id", table_name="metrics_multi_source_data")

    # 删除表
    op.drop_table("metrics_multi_source_data")
