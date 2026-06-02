#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checkpoint.py — Crawl state persistence for resume support.

Saves/loads crawl state so an interrupted crawl can continue without
re-requesting already-visited pages or re-processing the queue.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CrawlState:
    """Manages crawl progress state for checkpoint/resume."""

    def __init__(self, state_path: Path):
        self.state_path = Path(state_path)
        self.data: dict = {
            "config": {},
            "visited": [],
            "queued": [],
            "pending_queue": [],
            "current_depth": 0,
            "pages_crawled": 0,
            "started_at": None,
            "updated_at": None,
            "errors": [],
        }

    # ---- load / save ----

    def load(self) -> bool:
        """Load state from disk. Returns True if a prior state existed."""
        if not self.state_path.exists():
            return False
        try:
            self.data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def save(self) -> None:
        """Persist current state to disk."""
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---- state helpers ----

    def mark_started(self, config: dict) -> None:
        """Record crawl start parameters."""
        self.data["config"] = config
        self.data["started_at"] = datetime.now(timezone.utc).isoformat()
        self.data["pages_crawled"] = 0
        self.data["errors"] = []

    def is_visited(self, title: str) -> bool:
        """Check if a page has already been visited."""
        # Normalise for comparison
        key = title.strip().replace('_', ' ').lower()
        return key in {v.strip().replace('_', ' ').lower() for v in self.data["visited"]}

    def mark_visited(self, title: str) -> None:
        """Record a page as visited."""
        if not self.is_visited(title):
            self.data["visited"].append(title.strip())
        self.data["pages_crawled"] += 1

    def add_to_queue(self, items: list[dict]) -> None:
        """Add link dicts to the pending queue (avoiding duplicates)."""
        existing = {(q["title"].strip().lower()) for q in self.data["pending_queue"]}
        for item in items:
            key = item["title"].strip().lower()
            if key not in existing and not self.is_visited(item["title"]):
                self.data["pending_queue"].append(item)
                existing.add(key)

    def pop_next_batch(self, n: int) -> list[dict]:
        """Pop up to n items from the pending queue."""
        batch = self.data["pending_queue"][:n]
        self.data["pending_queue"] = self.data["pending_queue"][n:]
        return batch

    def queue_size(self) -> int:
        """Return number of items in the pending queue."""
        return len(self.data["pending_queue"])

    def record_error(self, error: dict) -> None:
        """Record a crawl error."""
        error["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.data["errors"].append(error)

    def get_summary(self) -> dict:
        """Return a human-readable summary of current state."""
        return {
            "pages_crawled": self.data["pages_crawled"],
            "pages_visited": len(self.data["visited"]),
            "queue_size": len(self.data["pending_queue"]),
            "current_depth": self.data["current_depth"],
            "started_at": self.data["started_at"],
            "error_count": len(self.data["errors"]),
        }
