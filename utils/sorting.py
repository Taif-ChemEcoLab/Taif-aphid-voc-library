"""Shared ordering helpers for published Bio identifiers."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


_BIO_ID = re.compile(r"^Bio(\d+)$", re.IGNORECASE)


def bio_id_number(value: object) -> int:
    """Return the numeric component of a Bio identifier, or a large fallback."""
    match = _BIO_ID.fullmatch(str(value).strip())
    return int(match.group(1)) if match else 10**9


def natural_bio_ids(values: Iterable[object]) -> list[object]:
    """Sort Bio1, Bio2, ... Bio10 without changing the identifier text."""
    return sorted(values, key=lambda value: (bio_id_number(value), str(value).casefold()))


def sort_by_bio_id(frame: pd.DataFrame, column: str = "bio_id", ascending: bool = True) -> pd.DataFrame:
    """Return a stable numeric Bio-ID ordering for a dataframe."""
    result = frame.copy()
    key = result[column].map(bio_id_number)
    return result.assign(_bio_sort_key=key).sort_values(
        ["_bio_sort_key", column], ascending=[ascending, ascending], kind="stable"
    ).drop(columns="_bio_sort_key").reset_index(drop=True)
