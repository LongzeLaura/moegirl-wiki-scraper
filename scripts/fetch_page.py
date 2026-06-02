#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_page.py — Scrape a single Moegirlpedia page and save its content.

Usage:
    python scripts/fetch_page.py "远坂凛"
    python scripts/fetch_page.py "远坂凛" --text          (extract plain text)
    python scripts/fetch_page.py "远坂凛" --api           (try API, other wikis)

Output:
    data/raw_wikitext/<safe_title>.html    — full HTML page source
    data/raw_wikitext/<safe_title>.txt     — extracted plain text (--text)
    data/raw_json/<safe_title>.json        — metadata
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_wikitext"
JSON_DIR = ROOT / "data" / "raw_json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
_RE_ILLEGAL = re.compile(r'[\\/:*?"<>|]+')


def safe_filename(title: str) -> str:
    """Sanitise a page title into a safe Windows filename."""
    s = _RE_ILLEGAL.sub('_', title).strip(' .')
    return s or '_'


def page_url(title: str) -> str:
    return f'https://zh.moegirl.org.cn/{quote(title, safe='')}'


# ---------------------------------------------------------------------------
#  HTTP fetch (curl_cffi → subprocess curl)
# ---------------------------------------------------------------------------

def _http_get(url: str) -> str | None:
    """Fetch a URL, trying curl_cffi impersonations then subprocess curl.

    Returns the response body on success (including 404 pages).
    Returns None only when every approach fails entirely.
    """
    from curl_cffi import requests as cffi

    sess = cffi.Session()
    sess.headers.update({
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    for impersonate in ("edge101", "safari15_5"):
        try:
            print(f"  GET (impersonate={impersonate})")
            r = sess.get(url, impersonate=impersonate, timeout=60)
            # Don't raise on 404 — Moegirlpedia returns 404 for missing pages.
            # We still want the HTML to analyse metadata.
            if r.status_code == 404:
                print(f"  [NOTE] HTTP 404 — page may not exist")
            else:
                r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  [WARN] {impersonate}: {e}")

    # Last resort: system curl
    print("  [INFO] Trying system curl...")
    import subprocess
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
#  HTML parsing
# ---------------------------------------------------------------------------

def _extract_meta(html: str) -> dict:
    """Pull page metadata out of MediaWiki's mw.config / page structure."""
    meta = {}

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
    # catlinks section: <li><a href="/Category:...">name</a></li>
    cat_section = re.search(
        r'<div[^>]*id="mw-normal-catlinks"[^>]*>(.*?)</div>', html, re.DOTALL
    )
    if cat_section:
        for a in re.finditer(
            r'<a\s[^>]*href="[^"]*Category:([^"]+)"[^>]*>([^<]+)</a>',
            cat_section.group(1),
        ):
            cats.append(a.group(2).strip())
    meta["categories"] = cats

    # --- is the page missing? ---
    # pageid=0 means the page doesn't exist on the wiki
    meta["exists"] = meta.get("pageid", 0) > 0

    return meta


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping script/style/head."""

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
    # prefer just the article content area
    body = re.search(
        r'<div[^>]*class="[^"]*mw-parser-output[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*printfooter',
        html, re.DOTALL,
    )
    source = body.group(1) if body else html
    parser = _TextExtractor()
    parser.feed(source)
    return parser.get_text()


# ---------------------------------------------------------------------------
#  Core scraper
# ---------------------------------------------------------------------------

def scrape_page(title: str, *, extract_text: bool = False) -> dict:
    """Scrape a single Moegirlpedia page and save to disk."""
    url = page_url(title)
    print(f"[...] Fetching: {title}")
    print(f"      URL: {url}")

    html = _http_get(url)
    if html is None:
        print("[ERROR] Could not fetch page — all approaches exhausted.", file=sys.stderr)
        sys.exit(1)

    meta = _extract_meta(html)
    page_title = meta.get("title", title)

    if not meta.get("exists"):
        print(f"[WARN] Page may not exist: {page_title}")

    # --- Save full HTML ---
    fname = safe_filename(page_title)
    html_path = RAW_DIR / f"{fname}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML  → {html_path}  ({len(html):,} bytes)")

    # --- Optionally extract plain text ---
    text_path = None
    if extract_text:
        text = extract_article_text(html)
        text_path = RAW_DIR / f"{fname}.txt"
        text_path.write_text(text, encoding="utf-8")
        print(f"  Text  → {text_path}  ({len(text):,} chars)")

    # --- Save metadata ---
    meta.update({
        "source_title": title,
        "url": url,
        "html_size": len(html),
        "method": "http_scrape",
    })
    json_path = JSON_DIR / f"{fname}.json"
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  JSON  → {json_path}")
    if meta.get("categories"):
        print(f"  Cats  → {len(meta['categories'])} categories")
    if meta.get("redirect"):
        print(f"  [NOTE] This page is a redirect.")

    return meta


# ---------------------------------------------------------------------------
#  API mode (for other wikis where the API allows content read)
# ---------------------------------------------------------------------------

def fetch_via_api(title: str) -> dict:
    """Try Pywikibot API — only works on wikis that allow content-read API."""
    import pywikibot
    from pywikibot import Page, Site

    site = Site("mgp", "mgp")
    print(f"[API] Site: {site}")
    print(f"[API] Logged in: {site.logged_in()}")

    page = Page(site, title)
    if not page.exists():
        raise pywikibot.exceptions.NoPageError(page)

    source_title = title
    if page.isRedirectPage():
        target = page.getRedirectTarget()
        print(f"[API] Redirect: {title} → {target.title()}")
        source_title = title
        page = target

    text = page.text

    meta = {
        "title": page.title(),
        "source_title": source_title,
        "url": page_url(page.title()),
        "text_length": len(text),
        "format": "application/x-wikitext",
        "method": "pywikibot_api",
        "pageid": page.pageid,
        "namespace": page.namespace().id,
        "edit_timestamp": str(page.editTime()) if page.editTime() else None,
    }

    fname = safe_filename(page.title())
    wiki_path = RAW_DIR / f"{fname}.wiki"
    json_path = JSON_DIR / f"{fname}.json"

    wiki_path.write_text(text, encoding="utf-8")
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  Wiki  → {wiki_path}  ({len(text):,} chars)")
    print(f"  JSON  → {json_path}")
    return meta


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(f"Usage:  python {sys.argv[0]} <title> [--text] [--api]", file=sys.stderr)
        print(f"        --text   Extract plain text from the scraped HTML", file=sys.stderr)
        print(f"        --api    Use Pywikibot API (for wikis that allow it)", file=sys.stderr)
        sys.exit(1)

    title = sys.argv[1].strip()
    use_api = "--api" in sys.argv
    extract_text = "--text" in sys.argv

    try:
        if use_api:
            fetch_via_api(title)
        else:
            scrape_page(title, extract_text=extract_text)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
