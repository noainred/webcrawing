"""Persist crawl results to JSON, JSON Lines or CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .models import Page

# Columns used for the (flat) CSV export. The full page text is intentionally
# omitted to keep the CSV readable; use JSON/JSONL if you need everything.
_CSV_FIELDS = [
    "url",
    "status_code",
    "depth",
    "title",
    "description",
    "content_type",
    "content_length",
    "fetched_at",
    "error",
    "links",
]


def save_json(pages: Iterable[Page], path: str | Path) -> None:
    data = [p.to_dict() for p in pages]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_jsonl(pages: Iterable[Page], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps(page.to_dict(), ensure_ascii=False) + "\n")


def save_csv(pages: Iterable[Page], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for page in pages:
            row = page.to_dict()
            row["links"] = " ".join(row.get("links", []))
            writer.writerow(row)


_WRITERS = {
    "json": save_json,
    "jsonl": save_jsonl,
    "ndjson": save_jsonl,
    "csv": save_csv,
}


def save(pages: Iterable[Page], path: str | Path, fmt: str | None = None) -> str:
    """Save ``pages`` to ``path``; format is inferred from the suffix if omitted.

    Returns the format that was used.
    """
    fmt = (fmt or Path(path).suffix.lstrip(".") or "json").lower()
    try:
        writer = _WRITERS[fmt]
    except KeyError:
        raise ValueError(f"unknown output format: {fmt!r} (use json, jsonl or csv)") from None
    writer(list(pages), path)
    return fmt
