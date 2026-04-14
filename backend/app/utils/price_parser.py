"""Price parsing helpers for XML import.

BUF XML uses Ukrainian number formatting:
- Thousands separator: U+00A0 (NBSP) or U+202F (narrow NBSP) or regular space.
- Decimal separator: comma (",") in most rows, but some rows use a dot.

Examples from TMC.xml:
    "1 015,16"      -> Decimal("1015.16")
    "999"           -> Decimal("999")
    "789,29"        -> Decimal("789.29")
    ""              -> None
    None            -> None
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

# Whitespace characters that may appear as thousands separators.
_WHITESPACE_CHARS = ("\xa0", "\u202f", " ", "\t", "\n", "\r")


def parse_price(raw: str | None) -> Decimal | None:
    """Parse a price string from BUF XML into a Decimal.

    Returns None for empty strings / None / invalid inputs.
    """
    if raw is None:
        return None
    value = raw
    for ch in _WHITESPACE_CHARS:
        value = value.replace(ch, "")
    if not value:
        return None
    # Normalise decimal comma to dot.
    value = value.replace(",", ".")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None
