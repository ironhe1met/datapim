"""Streaming XML parsers for BUF product/category feeds.

Uses `lxml.etree.iterparse` so the 16 MB TMC.xml never sits fully in memory.
Yields plain dicts with normalised Python types — the import service owns
the database side.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from lxml import etree

from app.utils.price_parser import parse_price

# --- Helpers ---------------------------------------------------------------


def _text(element: Any, tag: str) -> str | None:
    """Return the stripped text of a child tag, or None if empty/missing."""
    child = element.find(tag)
    if child is None:
        return None
    text = child.text
    if text is None:
        return None
    stripped = text.strip()
    return stripped or None


def _int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _bool_from(raw: str | None) -> bool:
    return (raw or "").strip().lower() == "true"


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse `2026-04-09T13:43` and a few common ISO variants."""
    if not raw:
        return None
    candidates = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _clear(element: Any) -> None:
    """Free memory after we're done with a parsed element."""
    element.clear()
    # Remove preceding siblings to keep the tree small.
    parent = element.getparent()
    if parent is not None:
        while element.getprevious() is not None:
            del parent[0]


# --- Products --------------------------------------------------------------


def iter_products(path: Path) -> Iterator[dict]:
    """Yield normalised product dicts from a BUF-format XML file.

    Source schema (per TMC.xml):
        <Catalog>
          <Product>
            <internal_code>...</internal_code>
            <sku>...</sku>
            <name>...</name>
            <brand/>
            <category_id>18003</category_id>
            <uktzed>...</uktzed>
            <country_of_origin/>
            <quantity>1</quantity>
            <in_stock>true</in_stock>
            <price_rrp>1 015,16</price_rrp>
            <currency>UAH</currency>
            <updated_at>2026-04-09T13:43</updated_at>
            <is_active>true</is_active>
          </Product>
          ...
        </Catalog>
    """
    context = etree.iterparse(
        str(path),
        events=("end",),
        tag="Product",
        recover=True,
        huge_tree=True,
    )
    for _event, elem in context:
        yield _build_product(elem)
        _clear(elem)
    del context


def _build_product(elem: Any) -> dict:
    internal_code = _text(elem, "internal_code") or ""
    sku_child = elem.find("sku")
    sku_raw = sku_child.text if sku_child is not None and sku_child.text is not None else ""
    sku = sku_raw.strip()

    price_raw = _text(elem, "price_rrp")
    currency = _text(elem, "currency") or "UAH"

    return {
        "internal_code": internal_code.strip(),
        "sku": sku,
        "name": _text(elem, "name"),
        "brand": _text(elem, "brand"),
        "category_id": _text(elem, "category_id"),
        "uktzed": _text(elem, "uktzed"),
        "country_of_origin": _text(elem, "country_of_origin"),
        "quantity": _int_or_none(_text(elem, "quantity")),
        "in_stock": _bool_from(_text(elem, "in_stock")),
        "price_rrp": parse_price(price_raw) if price_raw is not None else Decimal("0"),
        "currency": currency,
        "updated_at": _parse_dt(_text(elem, "updated_at")),
        "is_active": _bool_from(_text(elem, "is_active") or "true"),
    }


# --- Categories ------------------------------------------------------------


def iter_categories(path: Path) -> Iterator[dict]:
    """Yield normalised category dicts from a BUF-format XML file.

    Source schema (per TMCC.xml):
        <Categories>
          <category>
            <id>18003</id>
            <parent_id>18000</parent_id>
            <name>...</name>
            <is_active>true</is_active>
            <updated_at>2026-04-09T13:49</updated_at>
          </category>
          ...
        </Categories>
    """
    context = etree.iterparse(
        str(path),
        events=("end",),
        tag="category",
        recover=True,
        huge_tree=True,
    )
    for _event, elem in context:
        yield _build_category(elem)
        _clear(elem)
    del context


def _build_category(elem: Any) -> dict:
    return {
        "id": (_text(elem, "id") or "").strip(),
        "parent_id": _text(elem, "parent_id"),
        "name": _text(elem, "name") or "",
        "is_active": _bool_from(_text(elem, "is_active") or "true"),
        "updated_at": _parse_dt(_text(elem, "updated_at")),
    }
