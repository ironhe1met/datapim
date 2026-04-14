"""widen uktzed column

BUF feed packs UKTZED code + description into a single tag,
e.g. '8202310000X/Полотнадляторцювальнихпилок...' which overflows
the original VARCHAR(50). Widen to VARCHAR(255).

Revision ID: b2f3c4d5e6a7
Revises: a1f2c3d4e5b6
Create Date: 2026-04-15 00:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2f3c4d5e6a7"
down_revision: str | None = "a1f2c3d4e5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "uktzed",
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "uktzed",
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
