"""empty message

Revision ID: test
Revises: 9de9a8b8aa92
Create Date: 2025-10-23 02:17:04.513817

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "test"
down_revision: Union[str, None] = "9de9a8b8aa92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
