"""Merge multiple migration heads

Revision ID: 9ac2aff86228
Revises: 002_add_raw_scores_data_and_upgrade_jsonb, 005, 09d03cebf664, a20f91c49306
Create Date: 2025-09-25 14:22:58.998396

"""

# mypy: ignore-errors

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "9ac2aff86228"
down_revision: Union[str, Sequence[str]] = (
    "002_add_raw_scores_data_and_upgrade_jsonb",
    "005",
    "09d03cebf664",
    "a20f91c49306",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
