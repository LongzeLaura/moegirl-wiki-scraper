#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache.py — File-based cache for scraped pages.

Avoids re-requesting pages from Moegirlpedia by storing results locally.
Cache hit → return stored meta+text without HTTP request.
Cache miss / force → fetch fresh and update cache.
"""

import json
from pathlib import Path
from typing import Optional


class PageCache:
    """Simple file-based cache keyed by normalised page title."""

    def __init__(self, pages_dir: Path, text_dir: Path):
        self.pages_dir = Path(pages_dir)
        self.text_dir = Path(text_dir)
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.text_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, title: str) -> str:
        from .fetcher import safe_filename
        return safe_filename(title)

    def get(self, title: str) -> Optional[dict]:
        """Retrieve a cached page. Returns {meta, text} or None."""
        fname = self._safe_name(title)
        json_path = self.pages_dir / f"{fname}.json"
        txt_path = self.text_dir / f"{fname}.txt"

        if not json_path.exists():
            return None

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
            return {"meta": meta, "text": text}
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, title: str, meta: dict, text: str) -> None:
        """Store a page in the cache."""
        from .archiver import save_raw_page
        save_raw_page(
            title=title,
            meta=meta,
            text=text,
            pages_dir=self.pages_dir,
            text_dir=self.text_dir,
        )

    def has(self, title: str) -> bool:
        """Check if a page is cached."""
        fname = self._safe_name(title)
        return (self.pages_dir / f"{fname}.json").exists()

    def list_cached(self) -> list[str]:
        """List all cached page titles."""
        titles = []
        for p in self.pages_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                t = data.get("title") or data.get("source_title") or p.stem
                titles.append(t)
            except (json.JSONDecodeError, OSError):
                titles.append(p.stem)
        return titles
