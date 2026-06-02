#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetcher.py — Core HTTP fetch and HTML parsing functions for Moegirlpedia.

Extracted and abstracted from scripts/fetch_page.py so both the single-page
script and the FSN crawler can share the same fetch logic.
"""

import json
import re
import sys
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_RE_ILLEGAL = re.compile(r'[\\/:*?"<>|]+')


def safe_filename(title: str) -> str:
    """Sanitise a page title into a safe Windows filename."""
    s = _RE_ILLEGAL.sub('_', title).strip(' .')
    return s or '_'


def page_url(title: str) -> str:
    """Construct the full Moegirlpedia URL for a page title."""
    return f'https://zh.moegirl.org.cn/{quote(title, safe="")}'


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------

def http_get(
    url: str,
    *,
    impersonate_chain: Optional[list[str]] = None,
    timeout: int = 60,
    retries: int = 1,
    retry_delay: float = 10.0,
) -> Optional[str]:
    """Fetch a URL with TLS impersonation, falling back to system curl.

    Parameters
    ----------
    url : str
    impersonate_chain : list[str] or None
        TLS fingerprints to try (curl_cffi impersonate values).
        Defaults to ["edge101", "safari15_5"].
    timeout : int
        Request timeout in seconds for curl_cffi.
    retries : int
        Number of retries on transient failures.
    retry_delay : float
        Seconds to wait between retries.

    Returns
    -------
    str or None
        Response body on success; None when all approaches fail.
    """
    import time
    from curl_cffi import requests as cffi

    if impersonate_chain is None:
        impersonate_chain = ["edge101", "safari15_5"]

    sess = cffi.Session()
    sess.headers.update({
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    for attempt in range(retries):
        for impersonate in impersonate_chain:
            try:
                r = sess.get(url, impersonate=impersonate, timeout=timeout)
                if r.status_code == 404:
                    pass  # don't raise, we want the body
                else:
                    r.raise_for_status()
                return r.text
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(retry_delay)
                continue

    # Last resort: system curl
    try:
        p = subprocess.run(
            ["curl", "-sL", "--max-time", "30", url],
            capture_output=True, timeout=35,
        )
        if p.returncode == 0 and p.stdout:
            return p.stdout.decode("utf-8", errors="replace")
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# HTML metadata extraction
# ---------------------------------------------------------------------------

def extract_meta(html: str) -> dict:
    """Pull page metadata out of MediaWiki's mw.config / page structure.

    Returns a dict with keys: title, pageid, namespace, revision, redirect,
    content_model, categories, exists.
    """
    meta: dict = {}

    # --- basic identity ---
    if m := re.search(r'<title>(.+?)\s*-\s*.+?</title>', html):
        meta["title"] = m.group(1).strip()

    for key, pattern in [
        ("pageid",     r'"wgArticleId"\s*:\s*(\d+)'),
        ("namespace",  r'"wgNamespaceNumber"\s*:\s*(-?\d+)'),
        ("revision",   r'"wgRevisionId"\s*:\s*(\d+)'),
        ("redirect",   r'"wgIsRedirect"\s*:\s*(true|false)'),
        ("content_model", r'"wgPageContentModel"\s*:\s*"(\w+)"'),
    ]:
        if m := re.search(pattern, html):
            val = m.group(1)
            if val in ("true", "false"):
                val = val == "true"
            elif key in ("pageid", "namespace", "revision"):
                val = int(val)
            meta[key] = val

    # --- categories ---
    cats = []
    cat_section = re.search(
        r'<div[^>]*id="mw-normal-catlinks"[^>]*>(.*?)</div>', html, re.DOTALL,
    )
    if cat_section:
        for a in re.finditer(
            r'<a\s[^>]*href="[^"]*Category:([^"]+)"[^>]*>([^<]+)</a>',
            cat_section.group(1),
        ):
            cats.append(a.group(2).strip())
    meta["categories"] = cats

    # --- exists? ---
    meta["exists"] = meta.get("pageid", 0) > 0

    return meta


# ---------------------------------------------------------------------------
# Plain-text extraction
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping script/style/nav/footer."""

    def __init__(self):
        super().__init__()
        self._skip = False
        self._lines: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, _attrs):
        if tag in ("script", "style", "head", "nav", "footer"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "nav", "footer"):
            self._skip = False
        if tag in ("p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self._flush()

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data.strip())

    def _flush(self):
        line = ' '.join(b for b in self._buf if b)
        if line:
            self._lines.append(line)
        self._buf.clear()

    def get_text(self) -> str:
        self._flush()
        return '\n'.join(self._lines)


def extract_article_text(html: str) -> str:
    """Extract the article body text (mw-parser-output) from a MediaWiki page."""
    body = re.search(
        r'<div[^>]*class="[^"]*mw-parser-output[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*printfooter',
        html, re.DOTALL,
    )
    source = body.group(1) if body else html
    parser = _TextExtractor()
    parser.feed(source)
    return parser.get_text()


# ---------------------------------------------------------------------------
# Core scrape (returns data, does NOT save to disk)
# ---------------------------------------------------------------------------

def scrape_page(title: str) -> dict:
    """Scrape a single Moegirlpedia page and return {html, meta, text}.

    Does NOT save to disk — callers handle persistence.
    """
    url = page_url(title)
    html = http_get(url)
    if html is None:
        raise RuntimeError(f"Could not fetch page: {title}")

    meta = extract_meta(html)
    page_title = meta.get("title", title)
    text = extract_article_text(html)

    meta.update({
        "source_title": title,
        "url": url,
        "html_size": len(html),
        "method": "http_scrape",
    })

    return {
        "title": page_title,
        "html": html,
        "text": text,
        "meta": meta,
    }
