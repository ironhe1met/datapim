"""split product category into buf + custom

Splits `products.category_id` into `buf_category_id` + `custom_category_id`
to mirror the override pattern already used for name/brand/country (R-017).
Resolved category_id at read time = `custom_category_id ?? buf_category_id`.

Revision ID: a1f2c3d4e5b6
Revises: c4181ab0126d
Create Date: 2026-04-14 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f2c3d4e5b6"
down_revision: str | None = "c4181ab0126d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add the two new columns (nullable, FK to categories).
    op.add_column(
        "products",
        sa.Column("buf_category_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("custom_category_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_buf_category_id",
        "products",
        "categories",
        ["buf_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_products_custom_category_id",
        "products",
        "categories",
        ["custom_category_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. Backfill: existing category_id was import-assigned → move to BUF.
    op.execute(
        "UPDATE products SET buf_category_id = category_id WHERE category_id IS NOT NULL"
    )

    # 3. Drop old single-column index + column + its FK.
    op.drop_index("idx_products_category_id", table_name="products")
    op.drop_constraint("products_category_id_fkey", "products", type_="foreignkey")
    op.drop_column("products", "category_id")

    # 4. Add new indexes (mirroring the old one).
    op.create_index(
        "idx_products_buf_category_id", "products", ["buf_category_id"], unique=False
    )
    op.create_index(
        "idx_products_custom_category_id", "products", ["custom_category_id"], unique=False
    )


def downgrade() -> None:
    # Re-create the original single column, repopulate it from custom ?? buf,
    # then drop the split columns and their indexes.
    op.add_column(
        "products",
        sa.Column("category_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "products_category_id_fkey",
        "products",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "UPDATE products SET category_id = COALESCE(custom_category_id, buf_category_id)"
    )
    op.create_index(
        "idx_products_category_id", "products", ["category_id"], unique=False
    )

    op.drop_index("idx_products_custom_category_id", table_name="products")
    op.drop_index("idx_products_buf_category_id", table_name="products")
    op.drop_constraint("fk_products_custom_category_id", "products", type_="foreignkey")
    op.drop_constraint("fk_products_buf_category_id", "products", type_="foreignkey")
    op.drop_column("products", "custom_category_id")
    op.drop_column("products", "buf_category_id")
