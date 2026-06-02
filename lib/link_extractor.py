#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_extractor.py — Extract internal wiki links from Moegirlpedia HTML pages.

Since Moegirlpedia blocks the content-read API (prop=revisions → action-notallowed),
we parse intra-wiki links from the rendered HTML instead. We restrict extraction to
the mw-parser-output area to avoid nav/sidebar/footer noise.
"""

import re
from urllib.parse import unquote
from typing import Optional


# ---------------------------------------------------------------------------
# Title normalisation
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """Normalise a wiki page title for deduplication.

    Handles:
    - URL-encoded characters (%E8%BF%9C → 远)
    - HTML entities (&amp; → &)
    - Leading/trailing whitespace
    - Underscore ↔ space
    - Full-width / half-width variations (minimal)
    """
    import html as _html

    # URL decode
    decoded = unquote(title)

    # HTML entity decode (&amp; → &, etc.)
    decoded = _html.unescape(decoded)

    # Replace underscore with space (MediaWiki convention)
    decoded = decoded.replace('_', ' ')

    # Strip whitespace
    decoded = decoded.strip()

    # Collapse multiple spaces
    decoded = re.sub(r'\s+', ' ', decoded)

    return decoded


# ---------------------------------------------------------------------------
# Namespace detection
# ---------------------------------------------------------------------------

# MediaWiki namespaces we always want to skip for content crawling
DEFAULT_SKIP_NAMESPACES = {
    "User", "User talk",
    "Template", "Template talk",
    "File", "File talk",
    "Category", "Category talk",
    "Help", "Help talk",
    "MediaWiki", "MediaWiki talk",
    "Module", "Module talk",
    "Talk", "Talk",
    "Special",
    "萌娘百科", "萌娘百科 talk",
    "Project", "Project talk",
}

# Namespace prefixes that appear in URLs
KNOWN_NAMESPACE_PREFIXES = [
    "User:", "User_talk:",
    "Template:", "Template_talk:",
    "File:", "File_talk:",
    "Category:", "Category_talk:",
    "Help:", "Help_talk:",
    "MediaWiki:", "MediaWiki_talk:",
    "Module:", "Module_talk:",
    "Talk:",
    "Special:",
    "萌娘百科:", "萌娘百科_talk:",
    "Project:", "Project_talk:",
]


def extract_namespace(title: str) -> str:
    """Extract the namespace prefix from a page title, if any.

    Returns the namespace name (without colon) or empty string for mainspace.
    """
    for prefix in KNOWN_NAMESPACE_PREFIXES:
        if title.startswith(prefix):
            return prefix.rstrip(':_')
    # Also check for URL-encoded namespace
    for prefix in KNOWN_NAMESPACE_PREFIXES:
        encoded = prefix.replace(':', '%3A')
        if title.startswith(encoded):
            return prefix.rstrip(':_')
    return ""


def is_mainspace(title: str) -> bool:
    """Check if a page title is in the main (article) namespace."""
    return extract_namespace(title) == ""


# ---------------------------------------------------------------------------
# Link extraction from HTML
# ---------------------------------------------------------------------------

# Patterns for wiki-internal links in rendered HTML
# Moegirlpedia internal links look like: <a href="/<title>" ...>
# We want to avoid external links, red links (class="new"), and special pages.

_RE_INTERNAL_LINK = re.compile(
    r'<a\s[^>]*href="/([^"#:][^"]*?)"[^>]*>(.*?)</a>',
    re.DOTALL,
)

# Titles we never want to extract
_SKIP_TITLE_PATTERNS = [
    re.compile(p) for p in [
        r'^Special:',
        r'^Category:',
        r'^File:',
        r'^Talk:',
        r'^User:',
        r'^Template:',
        r'^Help:',
        r'^MediaWiki:',
        r'^Module:',
        r'^Portal:',
        r'^Topic:',
        r'^Thread:',
        r'^Project:',
        r'^萌娘百科:',
        r'^%[A-F0-9]{2}%3A',  # URL-encoded namespace colon
    ]
]


def _should_skip_title(title: str) -> bool:
    """Quick check: should we skip this title entirely?"""
    for pat in _SKIP_TITLE_PATTERNS:
        if pat.search(title):
            return True
    # Skip anchor-only links
    if title.startswith('#'):
        return True
    # Skip javascript / external URLs that somehow got in
    if title.startswith('javascript:') or title.startswith('http'):
        return True
    # Skip index.php action pages (edit, history, etc.)
    if title.startswith('index.php'):
        return True
    # Skip redlink (non-existent page) markers (handle both & and &amp;)
    if 'redlink=1' in title.lower() or 'redlink%3D1' in title.lower():
        return True
    # Skip action=raw, action=edit, etc.
    if 'action=' in title.lower() or 'action%3D' in title.lower():
        return True
    # Skip oldid=, diff=, etc.
    if 'oldid=' in title.lower():
        return True
    return False


def extract_links(html: str, source_title: str = "") -> list[dict]:
    """Extract internal wiki links from the article content area.

    Parameters
    ----------
    html : str
        Full HTML of the Moegirlpedia page.
    source_title : str
        Title of the source page, for context.

    Returns
    -------
    list[dict]
        Each dict: {"title": str, "display_text": str, "source_page": str}
    """
    # Focus on mw-parser-output for article links
    body = re.search(
        r'<div[^>]*class="[^"]*mw-parser-output[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*printfooter',
        html, re.DOTALL,
    )
    content = body.group(1) if body else html

    links: list[dict] = []
    seen: set[str] = set()

    for m in _RE_INTERNAL_LINK.finditer(content):
        raw_href = m.group(1)
        display_text = re.sub(r'<[^>]+>', '', m.group(2)).strip()

        title = normalize_title(raw_href)

        if _should_skip_title(title):
            continue

        if not title:
            continue

        # Deduplicate within this page
        if title.lower() in seen:
            continue
        seen.add(title.lower())

        links.append({
            "title": title,
            "display_text": display_text or title,
            "source_page": source_title,
        })

    return links


def extract_page_categories_from_text(categories: list[str]) -> list[str]:
    """Clean up category names extracted from page metadata."""
    return [c.strip() for c in categories if c.strip()]
