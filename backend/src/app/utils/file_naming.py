"""Rename a successfully-ingested statement file to its statement date, so the
watched folder is self-documenting (e.g. `2026-06-12.pdf` instead of a bank's
export filename)."""
from __future__ import annotations
import os
from pathlib import Path

from app.ingestion.base import RawTransaction


def rename_to_statement_date(filepath: str, raw_txns: list[RawTransaction]) -> str:
    """Rename `filepath` to `<latest txn date>.<ext>` in the same folder.
    Returns the (possibly unchanged) resulting path. No-ops if there are no
    transactions, the file is already correctly named, or the target already
    exists (assumed to be a different statement dropped the same day)."""
    if not raw_txns:
        return filepath

    stmt_date = max(t.date for t in raw_txns)
    src = Path(filepath)
    target_stem = stmt_date.isoformat()
    if src.stem == target_stem:
        return filepath

    target = src.with_name(f"{target_stem}{src.suffix}")
    if target.exists():
        n = 2
        while (candidate := src.with_name(f"{target_stem} ({n}){src.suffix}")).exists():
            n += 1
        target = candidate

    os.rename(src, target)
    return str(target)
