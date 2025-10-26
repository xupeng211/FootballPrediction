# mypy: ignore-errors
import sqlalchemy as sa
from alembic import op

"""Add MLOps support to predictions table

Revision ID: d82ea26f05d0
Revises: d6d814cc1078
Create Date: 2025-09-10 23:15:00.000000

"""

# revision identifiers, used by Alembic.
revision = "d82ea26f05d0"
down_revision = "d6d814cc1078"
branch_labels = None
depends_on = None

def upgrade() -> None:
    """添加MLOps支持到predictions表"""

    # 添加验证相关字段
    op.add_column(
        "predictions",
        sa.Column(
            "actual_result",
            sa.String(10),
            nullable=True,
            comment="实际比赛结果",
        ),
    )
    op.add_column(
        "predictions",
        sa.Column("is_correct", sa.Boolean(), nullable=True, comment="预测是否正确"),
    )
    op.add_column(
        "predictions",
        sa.Column("verified_at", sa.DateTime(), nullable=True, comment="验证时间"),
    )

    # 添加特征数据和元数据字段
    op.add_column(
        "predictions",
        sa.Column(
            "features_used",
            sa.JSON(),
            nullable=True,
            comment="预测时使用的特征数据",
        ),
    )
    op.add_column(
        "predictions",
        sa.Column(
            "prediction_metadata",
            sa.JSON(),
            nullable=True,
            comment="预测相关的元数据",
        ),
    )

    # 添加新的索引来优化查询性能
    op.create_index(
        "idx_predictions_verification", "predictions", ["is_correct", "verified_at"]
    )
    op.create_index("idx_predictions_actual_result", "predictions", ["actual_result"])

def downgrade() -> None:
    """移除MLOps支持字段"""

    # 删除索引
    op.drop_index("idx_predictions_actual_result", table_name="predictions")
    op.drop_index("idx_predictions_verification", table_name="predictions")

    # 删除字段
    op.drop_column("predictions", "prediction_metadata")
    op.drop_column("predictions", "features_used")
    op.drop_column("predictions", "verified_at")
    op.drop_column("predictions", "is_correct")
    op.drop_column("predictions", "actual_result")
