"""Add provider field to odds table

Revision ID: add_provider_to_odds
Revises: previous_migration
Create Date: 2025-12-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_provider_to_odds'
down_revision: Union[str, None] = 'previous_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加provider字段到odds表"""
    op.add_column('odds', sa.Column('provider', sa.String(length=50), nullable=True))
    op.create_index('ix_odds_provider', 'odds', ['provider'])


def downgrade() -> None:
    """移除provider字段"""
    op.drop_index('ix_odds_provider', table_name='odds')
    op.drop_column('odds', 'provider')