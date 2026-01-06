"""Initial migration - create odds table

Revision ID: 001
Revises:
Create Date: 2024-12-17 21:25:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create odds table"""
    # Create odds table
    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("match_id", sa.String(length=100), nullable=False, comment="比赛ID"),
        sa.Column("home_team", sa.String(length=100), nullable=False, comment="主队名称"),
        sa.Column("away_team", sa.String(length=100), nullable=False, comment="客队名称"),
        sa.Column("match_date", sa.DateTime(), nullable=False, comment="比赛时间"),
        sa.Column("league", sa.String(length=100), nullable=True, comment="联赛名称"),
        sa.Column("bookmaker", sa.String(length=100), nullable=False, comment="博彩公司"),
        sa.Column("home_odds", sa.Float(), nullable=True, comment="主胜赔率"),
        sa.Column("draw_odds", sa.Float(), nullable=True, comment="平局赔率"),
        sa.Column("away_odds", sa.Float(), nullable=True, comment="客胜赔率"),
        sa.Column("implied_home_prob", sa.Float(), nullable=True, comment="主胜隐含概率"),
        sa.Column("implied_draw_prob", sa.Float(), nullable=True, comment="平局隐含概率"),
        sa.Column("implied_away_prob", sa.Float(), nullable=True, comment="客胜隐含概率"),
        sa.Column("data_source", sa.String(length=50), nullable=True, comment="数据来源"),
        sa.Column("collected_at", sa.DateTime(), nullable=True, comment="数据收集时间"),
        sa.Column("is_active", sa.Boolean(), nullable=True, comment="是否有效"),
        sa.PrimaryKeyConstraint("id"),
        comment="赔率数据表",
    )

    # Create indexes for better query performance
    op.create_index(op.f("ix_odds_match_id"), "odds", ["match_id"], unique=False)
    op.create_index(op.f("ix_odds_bookmaker"), "odds", ["bookmaker"], unique=False)
    op.create_index(op.f("ix_odds_match_date"), "odds", ["match_date"], unique=False)


def downgrade() -> None:
    """Drop odds table"""
    op.drop_table("odds")
