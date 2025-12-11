"""Add Titan007 Dual Table Architecture

Revision ID: add_titan_dual_table_architecture
Revises: 005_add_multi_tenant_support
Create Date: 2024-12-12 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_titan_dual_table_architecture"
down_revision = "005_add_multi_tenant_support"
branch_labels = None
depends_on = None


def upgrade():
    """Implement Titan007 Dual Table Architecture - Latest + History Tables"""

    # Create TitanEuroOddsLatest table
    op.create_table(
        "titan_euro_odds_latest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("home_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("draw_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("away_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("home_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("draw_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("away_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_euro_odds_latest_created_at"),
        "titan_euro_odds_latest",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_latest_id"),
        "titan_euro_odds_latest",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_latest_match_id"),
        "titan_euro_odds_latest",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_latest_bookmaker_id"),
        "titan_euro_odds_latest",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_euro_latest_match_bookmaker",
        "titan_euro_odds_latest",
        ["match_id", "bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_euro_latest_update_time",
        "titan_euro_odds_latest",
        ["update_time"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_euro_latest_match_bookmaker",
        "titan_euro_odds_latest",
        sa.UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_euro_latest_match_bookmaker"
        ),
    )

    # Create TitanEuroOddsHistory table
    op.create_table(
        "titan_euro_odds_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("home_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("draw_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("away_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("home_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("draw_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("away_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_euro_odds_history_created_at"),
        "titan_euro_odds_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_history_id"),
        "titan_euro_odds_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_history_match_id"),
        "titan_euro_odds_history",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_euro_odds_history_bookmaker_id"),
        "titan_euro_odds_history",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_euro_history_match_time",
        "titan_euro_odds_history",
        ["match_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_euro_history_bookmaker_time",
        "titan_euro_odds_history",
        ["bookmaker_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_euro_history_update_time",
        "titan_euro_odds_history",
        ["update_time DESC"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_euro_history_match_bookmaker_time",
        "titan_euro_odds_history",
        sa.UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_euro_history_match_bookmaker_time",
        ),
    )

    # Create TitanAsianOddsLatest table
    op.create_table(
        "titan_asian_odds_latest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("upper_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("lower_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("handicap", sa.String(length=20), nullable=True),
        sa.Column("upper_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("lower_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("handicap_open", sa.String(length=20), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_asian_odds_latest_created_at"),
        "titan_asian_odds_latest",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_latest_id"),
        "titan_asian_odds_latest",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_latest_match_id"),
        "titan_asian_odds_latest",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_latest_bookmaker_id"),
        "titan_asian_odds_latest",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_asian_latest_match_bookmaker",
        "titan_asian_odds_latest",
        ["match_id", "bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_asian_latest_update_time",
        "titan_asian_odds_latest",
        ["update_time"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_asian_latest_match_bookmaker",
        "titan_asian_odds_latest",
        sa.UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_asian_latest_match_bookmaker"
        ),
    )

    # Create TitanAsianOddsHistory table
    op.create_table(
        "titan_asian_odds_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("upper_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("lower_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("handicap", sa.String(length=20), nullable=True),
        sa.Column("upper_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("lower_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("handicap_open", sa.String(length=20), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_asian_odds_history_created_at"),
        "titan_asian_odds_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_history_id"),
        "titan_asian_odds_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_history_match_id"),
        "titan_asian_odds_history",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_asian_odds_history_bookmaker_id"),
        "titan_asian_odds_history",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_asian_history_match_time",
        "titan_asian_odds_history",
        ["match_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_asian_history_bookmaker_time",
        "titan_asian_odds_history",
        ["bookmaker_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_asian_history_update_time",
        "titan_asian_odds_history",
        ["update_time DESC"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_asian_history_match_bookmaker_time",
        "titan_asian_odds_history",
        sa.UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_asian_history_match_bookmaker_time",
        ),
    )

    # Create TitanOverUnderOddsLatest table
    op.create_table(
        "titan_overunder_odds_latest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("over_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("under_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("overunder", sa.String(length=20), nullable=True),
        sa.Column("over_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("under_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("overunder_open", sa.String(length=20), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_latest_created_at"),
        "titan_overunder_odds_latest",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_latest_id"),
        "titan_overunder_odds_latest",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_latest_match_id"),
        "titan_overunder_odds_latest",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_latest_bookmaker_id"),
        "titan_overunder_odds_latest",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_overunder_latest_match_bookmaker",
        "titan_overunder_odds_latest",
        ["match_id", "bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_overunder_latest_update_time",
        "titan_overunder_odds_latest",
        ["update_time"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_overunder_latest_match_bookmaker",
        "titan_overunder_odds_latest",
        sa.UniqueConstraint(
            "match_id", "bookmaker_id", name="uq_titan_overunder_latest_match_bookmaker"
        ),
    )

    # Create TitanOverUnderOddsHistory table
    op.create_table(
        "titan_overunder_odds_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=50), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("over_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("under_odds", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("overunder", sa.String(length=20), nullable=True),
        sa.Column("over_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("under_open", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("overunder_open", sa.String(length=20), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"],
            ["titan_bookmakers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_history_created_at"),
        "titan_overunder_odds_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_history_id"),
        "titan_overunder_odds_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_history_match_id"),
        "titan_overunder_odds_history",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_titan_overunder_odds_history_bookmaker_id"),
        "titan_overunder_odds_history",
        ["bookmaker_id"],
        unique=False,
    )
    op.create_index(
        "idx_titan_overunder_history_match_time",
        "titan_overunder_odds_history",
        ["match_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_overunder_history_bookmaker_time",
        "titan_overunder_odds_history",
        ["bookmaker_id", "update_time DESC"],
        unique=False,
    )
    op.create_index(
        "idx_titan_overunder_history_update_time",
        "titan_overunder_odds_history",
        ["update_time DESC"],
        unique=False,
    )
    op.create_constraint(
        "uq_titan_overunder_history_match_bookmaker_time",
        "titan_overunder_odds_history",
        sa.UniqueConstraint(
            "match_id",
            "bookmaker_id",
            "update_time",
            name="uq_titan_overunder_history_match_bookmaker_time",
        ),
    )


def downgrade():
    """Rollback Titan007 Dual Table Architecture"""

    # Drop tables in reverse order
    op.drop_table("titan_overunder_odds_history")
    op.drop_table("titan_overunder_odds_latest")
    op.drop_table("titan_asian_odds_history")
    op.drop_table("titan_asian_odds_latest")
    op.drop_table("titan_euro_odds_history")
    op.drop_table("titan_euro_odds_latest")
