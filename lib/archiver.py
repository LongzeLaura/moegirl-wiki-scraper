#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archiver.py — Save scraped pages as raw JSON/TXT and as categorized Markdown.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Metadata header builder
# ---------------------------------------------------------------------------

def _build_frontmatter(
    *,
    title: str,
    source: str,
    source_page: str,
    category: str,
    crawl_depth: int,
    related_pages: Optional[list[str]] = None,
    extra: Optional[dict] = None,
) -> str:
    """Build a YAML frontmatter block for an archived page."""
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"title: {title}",
        f"source: {source}",
        f"source_page: {source_page}",
        f"fetched_at: {fetched_at}",
        f"category: {category}",
        f"crawl_depth: {crawl_depth}",
    ]
    if related_pages:
        lines.append("related_pages:")
        for rp in related_pages:
            lines.append(f"  - {rp}")
    if extra:
        for k, v in extra.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Raw page saving
# ---------------------------------------------------------------------------

def save_raw_page(
    *,
    title: str,
    meta: dict,
    text: str,
    html: Optional[str] = None,
    pages_dir: Path,
    text_dir: Path,
) -> tuple[Path, Path]:
    """Save raw page data as JSON metadata and plain text.

    Parameters
    ----------
    title : str
    meta : dict
    text : str
    html : str or None
    pages_dir : Path
    text_dir : Path

    Returns
    -------
    (json_path, txt_path)
    """
    from .fetcher import safe_filename

    fname = safe_filename(title)
    pages_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    json_path = pages_dir / f"{fname}.json"
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    txt_path = text_dir / f"{fname}.txt"
    txt_path.write_text(text, encoding="utf-8")

    return json_path, txt_path


# ---------------------------------------------------------------------------
# Markdown page saving
# ---------------------------------------------------------------------------

def save_markdown_page(
    *,
    title: str,
    text: str,
    category: str,
    meta: dict,
    crawl_depth: int = 0,
    related_pages: Optional[list[str]] = None,
    source: str = "moegirl",
    sources_dir: Path,
    wiki_dir: Path,
    category_reason: Optional[dict] = None,
) -> dict:
    """Save a page as categorized Markdown in the wiki/ directory.

    Parameters
    ----------
    title : str
    text : str
    category : str — one of characters, world, locations, factions, items, plot-arcs, uncategorized
    meta : dict
    crawl_depth : int
    related_pages : list[str] or None
    source : str — "moegirl" or similar source identifier
    sources_dir : Path — base directory for source copies (wiki/sources/moegirl/)
    wiki_dir : Path — base directory for categorized pages (wiki/)
    category_reason : dict or None — classification reason details

    Returns
    -------
    dict with paths of saved files.
    """
    from .fetcher import safe_filename

    fname = safe_filename(title)
    source_page = meta.get("source_title", title)
    categories = meta.get("categories", [])

    # Build frontmatter
    extra = {}
    if categories:
        extra["page_categories"] = categories
    if category_reason:
        extra["category_reason"] = json.dumps(category_reason, ensure_ascii=False)

    frontmatter = _build_frontmatter(
        title=title,
        source=source,
        source_page=source_page,
        category=category,
        crawl_depth=crawl_depth,
        related_pages=related_pages,
        extra=extra,
    )

    # Build body
    body_parts = [
        f"# {title}",
        "",
        "## 来源说明",
        f"本文来自萌娘百科页面 [{source_page}](https://zh.moegirl.org.cn/{source_page}) 的文本抽取，",
        "仅作为本地设定整理来源。版权归属萌娘百科及原作者。",
        "",
        "## 正文",
        "",
        text,
        "",
    ]

    if related_pages:
        body_parts.append("## 抽取到的相关页面")
        body_parts.append("")
        for rp in related_pages:
            body_parts.append(f"- [[{rp}]]")
        body_parts.append("")

    body = "\n".join(body_parts)
    content = frontmatter + body

    saved_paths = {}

    # 1. Save to wiki/sources/moegirl/
    sources_dir.mkdir(parents=True, exist_ok=True)
    source_path = sources_dir / f"{fname}.md"
    source_path.write_text(content, encoding="utf-8")
    saved_paths["source"] = str(source_path)

    # 2. Save to categorized directory
    cat_dir = wiki_dir / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    cat_path = cat_dir / f"{fname}.md"
    cat_path.write_text(content, encoding="utf-8")
    saved_paths["category"] = str(cat_path)

    return saved_paths
