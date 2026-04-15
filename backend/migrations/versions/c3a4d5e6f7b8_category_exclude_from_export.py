"""category exclude_from_export flag

Per-category opt-out from public XML export. When set, the category
itself and all its descendants (and the products within) are silently
omitted from /export/products.xml and /export/categories.xml.

Use case: BUF feed includes "Послуги" / "Удалённые" branches that
should never reach the partner XML. Operator toggles the flag in UI.

Revision ID: c3a4d5e6f7b8
Revises: b2f3c4d5e6a7
Create Date: 2026-04-15 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a4d5e6f7b8"
down_revision: str | None = "b2f3c4d5e6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "exclude_from_export",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("categories", "exclude_from_export")
