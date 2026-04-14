"""Category CRUD business logic."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product
from app.schemas.category import (
    CategoryCreate,
    CategoryTreeNode,
    CategoryUpdate,
)


async def _compute_product_counts(db: AsyncSession) -> dict[UUID, int]:
    """Live recursive product_count: own products + all descendants'."""
    # 1) Direct counts per category via resolved category (custom ?? buf).
    resolved = func.coalesce(Product.custom_category_id, Product.buf_category_id)
    direct_stmt = (
        select(resolved.label("cat_id"), func.count(Product.id))
        .where(resolved.is_not(None))
        .group_by(resolved)
    )
    direct_result = await db.execute(direct_stmt)
    direct: dict[UUID, int] = {row[0]: int(row[1]) for row in direct_result.all()}

    # 2) Load all categories to build the parent→children map.
    cats_stmt = select(Category.id, Category.parent_id)
    cats_rows = (await db.execute(cats_stmt)).all()
    children_map: dict[UUID, list[UUID]] = {}
    all_ids: list[UUID] = []
    for cid, parent_id in cats_rows:
        all_ids.append(cid)
        if parent_id is not None:
            children_map.setdefault(parent_id, []).append(cid)

    # 3) Post-order DFS to accumulate descendants' counts; iterative to avoid
    #    recursion limits on large trees.
    totals: dict[UUID, int] = {cid: direct.get(cid, 0) for cid in all_ids}
    roots = [cid for cid, parent_id in cats_rows if parent_id is None]
    stack: list[tuple[UUID, bool]] = [(r, False) for r in roots]
    while stack:
        node, expanded = stack.pop()
        if not expanded:
            stack.append((node, True))
            for child in children_map.get(node, []):
                stack.append((child, False))
        else:
            for child in children_map.get(node, []):
                totals[node] += totals[child]
    return totals


def _not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Категорію не знайдено", "code": "NOT_FOUND"},
    )


def _parent_not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Батьківську категорію не знайдено", "code": "PARENT_NOT_FOUND"},
    )


def _invalid_parent_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "Виявлено циклічну ієрархію", "code": "INVALID_PARENT"},
    )


async def list_categories_flat(db: AsyncSession) -> list[Category]:
    """Return all categories ordered by name, with live product_count."""
    stmt = select(Category).order_by(Category.name.asc())
    result = await db.execute(stmt)
    cats = list(result.scalars().all())
    counts = await _compute_product_counts(db)
    for c in cats:
        c.product_count = counts.get(c.id, 0)
    return cats


async def list_categories_tree(db: AsyncSession) -> list[CategoryTreeNode]:
    """Load all categories once and assemble a nested tree in Python (O(N))."""
    flat = await list_categories_flat(db)
    nodes: dict[UUID, CategoryTreeNode] = {c.id: CategoryTreeNode.model_validate(c) for c in flat}
    roots: list[CategoryTreeNode] = []
    for cat in flat:
        node = nodes[cat.id]
        if cat.parent_id is not None and cat.parent_id in nodes:
            nodes[cat.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


async def get_category(db: AsyncSession, category_id: UUID) -> Category | None:
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_direct_children(db: AsyncSession, category_id: UUID) -> list[Category]:
    stmt = select(Category).where(Category.parent_id == category_id).order_by(Category.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_breadcrumb(db: AsyncSession, category: Category) -> list[Category]:
    """Walk up parent_id chain; return list from root to the given category (inclusive)."""
    chain: list[Category] = [category]
    seen: set[UUID] = {category.id}
    current = category
    while current.parent_id is not None:
        if current.parent_id in seen:  # pragma: no cover - DB integrity guard
            break
        parent = await get_category(db, current.parent_id)
        if parent is None:
            break
        chain.append(parent)
        seen.add(parent.id)
        current = parent
    chain.reverse()
    return chain


async def get_category_with_details(
    db: AsyncSession, category_id: UUID
) -> tuple[Category, list[Category], list[Category]]:
    """Return (category, direct_children, breadcrumb). Raises 404 if not found."""
    category = await get_category(db, category_id)
    if category is None:
        raise _not_found_exc()
    children = await _get_direct_children(db, category_id)
    breadcrumb = await _get_breadcrumb(db, category)
    counts = await _compute_product_counts(db)
    category.product_count = counts.get(category.id, 0)
    for c in children:
        c.product_count = counts.get(c.id, 0)
    return category, children, breadcrumb


async def _external_id_taken(db: AsyncSession, external_id: str) -> bool:
    stmt = select(Category.id).where(Category.external_id == external_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    if data.parent_id is not None:
        parent = await get_category(db, data.parent_id)
        if parent is None:
            raise _parent_not_found_exc()

    external_id = data.external_id
    if not external_id:
        # Auto-generate; loop in the extremely unlikely case of a collision.
        while True:
            candidate = f"USER-{uuid4().hex[:8]}"
            if not await _external_id_taken(db, candidate):
                external_id = candidate
                break
    elif await _external_id_taken(db, external_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "external_id вже зайнятий", "code": "DUPLICATE_EXTERNAL_ID"},
        )

    category = Category(
        external_id=external_id,
        parent_id=data.parent_id,
        name=data.name,
        is_active=True,
        product_count=0,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _would_create_cycle(db: AsyncSession, category_id: UUID, new_parent_id: UUID) -> bool:
    """True if setting `new_parent_id` on `category_id` would create a cycle.

    Walk up from new_parent_id; if we visit category_id, it's a cycle.
    """
    if new_parent_id == category_id:
        return True

    visited: set[UUID] = set()
    current_id: UUID | None = new_parent_id
    while current_id is not None:
        if current_id == category_id:
            return True
        if current_id in visited:  # pragma: no cover - defensive
            return True
        visited.add(current_id)
        parent = await get_category(db, current_id)
        if parent is None:
            return False
        current_id = parent.parent_id
    return False


async def update_category(db: AsyncSession, category_id: UUID, data: CategoryUpdate) -> Category:
    category = await get_category(db, category_id)
    if category is None:
        raise _not_found_exc()

    fields_set = data.model_fields_set

    if "name" in fields_set and data.name is not None:
        category.name = data.name

    if "parent_id" in fields_set:
        new_parent_id = data.parent_id
        if new_parent_id is None:
            category.parent_id = None
        else:
            if new_parent_id == category_id:
                raise _invalid_parent_exc()
            parent = await get_category(db, new_parent_id)
            if parent is None:
                raise _parent_not_found_exc()
            if await _would_create_cycle(db, category_id, new_parent_id):
                raise _invalid_parent_exc()
            category.parent_id = new_parent_id

    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
