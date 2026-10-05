"""Researcher-facing table cleanup without altering the underlying V1 schema."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


MISSING_TOKENS = {
    "", "none", "nan", "null", "unknown", "unresolved", "not_available",
    "not available", "not_applicable", "not applicable", "not assigned", "n/a", "false",
}


def _supported(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    return series.notna() & ~text.str.casefold().isin(MISSING_TOKENS)


def researcher_table(
    frame: pd.DataFrame,
    labels: Mapping[str, str],
    *,
    always_keep: Sequence[str] = (),
    minimum_supported_fraction: float = 0.5,
    missing_label: str = "Not available",
) -> pd.DataFrame:
    """Hide empty/internal columns and rename supported fields for researchers."""
    if frame.empty:
        return frame.copy()
    selected: list[str] = []
    for column in labels:
        if column not in frame.columns:
            continue
        fraction = float(_supported(frame[column]).mean())
        if column in always_keep or fraction >= minimum_supported_fraction:
            selected.append(column)
    result = frame[selected].copy()
    for column in selected:
        mask = ~_supported(result[column])
        if mask.any() and column in always_keep:
            result.loc[mask, column] = missing_label
    return result.rename(columns={column: labels[column] for column in selected})
