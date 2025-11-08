from collections.abc import Sequence

"""empty message"

Revision ID: test
Revises: 9de9a8b8aa92
Create Date: 2025-10-23 02:17:04.513817

"""

revision: str = "test"
down_revision: str | None = "9de9a8b8aa92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
