"""add short_description, video_url, internal_notes

Revision ID: d4e5f6a7b8c9
Revises: c3a4d5e6f7b8
Create Date: 2026-04-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3a4d5e6f7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("short_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("video_url", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("internal_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "internal_notes")
    op.drop_column("products", "video_url")
    op.drop_column("products", "short_description")
