#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawl_fsn.py — Controlled, low-risk FSN-focused crawler for Moegirlpedia.

Fetches pages within strict boundaries (max_depth, max_pages, relevance filter),
archives raw data, and classifies content into FSN setting categories.

Usage:
    python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --delay 5
    python scripts/crawl_fsn.py --seeds config/fsn_seeds.txt --max-depth 2 --max-pages 80
    python scripts/crawl_fsn.py --dry-run --seed "间桐樱" --max-depth 1
    python scripts/crawl_fsn.py --seed "间桐樱" --resume
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — ensure we can import lib/
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.fetcher import scrape_page, safe_filename
from lib.link_extractor import extract_links, normalize_title, is_mainspace
from lib.relevance import (
    score_page_relevance,
    is_allowed_page,
    is_fsn_page,
    DEFAULT_INCLUDE_KEYWORDS,
    DEFAULT_EXCLUDE_KEYWORDS,
)
from lib.classifier import classify_page
from lib.archiver import save_raw_page, save_markdown_page
from lib.cache import PageCache
from lib.checkpoint import CrawlState


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML config file. Requires PyYAML."""
    try:
        import yaml
    except ImportError:
        print("[ERROR] PyYAML is required to read config files.", file=sys.stderr)
        print("        Install it with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_keywords_file(path: Path) -> list[str]:
    """Load a keyword list from a text file (one per line, # comments, blank lines ignored)."""
    if not path.exists():
        return []
    keywords = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            keywords.append(line)
    return keywords


def _load_seeds_file(path: Path) -> list[str]:
    """Load seed pages from a text file."""
    return _load_keywords_file(path)


def load_config(args: argparse.Namespace) -> dict:
    """Load and merge configuration from YAML + CLI args.

    CLI args take precedence over YAML values.
    """
    # Default config
    cfg: dict = {
        "seeds": [],
        "max_depth": 1,
        "max_pages": 50,
        "delay_seconds": 4.0,
        "jitter_ratio": 0.3,
        "max_retries": 3,
        "retry_base_delay": 10.0,
        "min_relevance_score": 8,
        "fsn_page_threshold": 15,
        "include_keywords": DEFAULT_INCLUDE_KEYWORDS,
        "exclude_keywords": DEFAULT_EXCLUDE_KEYWORDS,
        "allowed_namespaces": [],
        "category_rules": {},
        "output_paths": {
            "raw_base": "data/raw/moegirl",
            "wiki_base": "wiki",
            "sources_dir": "wiki/sources/moegirl",
            "state_file": "data/raw/moegirl/crawl_state.json",
            "log_file": "data/raw/moegirl/crawl_log.jsonl",
        },
        "dry_run": False,
        "force": False,
    }

    # Load YAML config if specified
    config_path = args.config
    if config_path:
        yaml_path = Path(config_path)
    else:
        yaml_path = ROOT / "config" / "fsn_crawl.yaml"

    if yaml_path.exists():
        yaml_cfg = _load_yaml(yaml_path)
        _deep_merge(cfg, yaml_cfg)

    # Load keyword files from config paths
    inc_file = cfg.get("include_keywords_file", "")
    if inc_file:
        inc_path = Path(inc_file)
        if not inc_path.is_absolute():
            inc_path = ROOT / inc_path
        if inc_path.exists():
            cfg["include_keywords"] = _load_keywords_file(inc_path)

    exc_file = cfg.get("exclude_keywords_file", "")
    if exc_file:
        exc_path = Path(exc_file)
        if not exc_path.is_absolute():
            exc_path = ROOT / exc_path
        if exc_path.exists():
            cfg["exclude_keywords"] = _load_keywords_file(exc_path)

    # ---- CLI overrides ----

    if args.seed:
        cfg["seeds"] = [args.seed]
    elif args.seeds:
        seeds_path = Path(args.seeds)
        if not seeds_path.is_absolute():
            seeds_path = ROOT / seeds_path
        if seeds_path.exists():
            cfg["seeds"] = _load_seeds_file(seeds_path)
        else:
            print(f"[ERROR] Seeds file not found: {seeds_path}", file=sys.stderr)
            sys.exit(1)

    if args.max_depth is not None:
        cfg["max_depth"] = args.max_depth
    if args.max_pages is not None:
        cfg["max_pages"] = args.max_pages
    if args.delay is not None:
        cfg["delay_seconds"] = args.delay
    if args.jitter is not None:
        cfg["jitter_ratio"] = args.jitter
    if args.max_retries is not None:
        cfg["max_retries"] = args.max_retries
    if args.force:
        cfg["force"] = True
    if args.dry_run:
        cfg["dry_run"] = True
    if args.include_keywords:
        inc_path = Path(args.include_keywords)
        if inc_path.exists():
            cfg["include_keywords"] = _load_keywords_file(inc_path)
    if args.exclude_keywords:
        exc_path = Path(args.exclude_keywords)
        if exc_path.exists():
            cfg["exclude_keywords"] = _load_keywords_file(exc_path)
    if args.output_dir:
        cfg["output_paths"]["raw_base"] = f"{args.output_dir}/raw/moegirl"
        cfg["output_paths"]["wiki_base"] = args.output_dir
        cfg["output_paths"]["sources_dir"] = f"{args.output_dir}/sources/moegirl"
        cfg["output_paths"]["state_file"] = f"{args.output_dir}/raw/moegirl/crawl_state.json"
        cfg["output_paths"]["log_file"] = f"{args.output_dir}/raw/moegirl/crawl_log.jsonl"

    return cfg


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base (mutates base)."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class CrawlLogger:
    """Append-only JSONL logger for crawl events."""

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None

    def open(self) -> None:
        self._file = open(self.log_path, "a", encoding="utf-8")

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def log(self, event: str, **kwargs) -> None:
        """Log an event with timestamp."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **kwargs,
        }
        line = json.dumps(entry, ensure_ascii=False)
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()
        # Also print a short summary to stdout
        print(f"  [LOG] {event}: {_summarize(kwargs)}")


def _summarize(kwargs: dict) -> str:
    """Short human-readable summary of a log entry."""
    parts = []
    for k, v in kwargs.items():
        if isinstance(v, (list, dict)):
            v = f"({len(v)} items)"
        elif isinstance(v, str) and len(v) > 60:
            v = v[:57] + "..."
        parts.append(f"{k}={v}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Polite delay
# ---------------------------------------------------------------------------

def polite_delay(delay_seconds: float, jitter_ratio: float) -> None:
    """Sleep for delay_seconds ± jitter_ratio with random jitter."""
    if delay_seconds <= 0:
        return
    jitter = delay_seconds * jitter_ratio * (random.random() * 2 - 1)
    actual = max(0.5, delay_seconds + jitter)
    time.sleep(actual)


def retry_delay(retry_count: int, base_delay: float) -> float:
    """Exponential backoff: base_delay * 2^(retry_count-1)."""
    return base_delay * (2 ** (retry_count - 1))


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

class FSNCrawler:
    """BFS crawler with relevance filtering, caching, and checkpointing."""

    def __init__(self, cfg: dict, resume: bool = False):
        self.cfg = cfg
        self.resume_flag = resume

        # Output paths
        op = cfg["output_paths"]
        self.raw_base = ROOT / op["raw_base"]
        self.wiki_base = ROOT / op["wiki_base"]
        self.sources_dir = ROOT / op["sources_dir"]
        self.pages_dir = self.raw_base / "pages"
        self.text_dir = self.raw_base / "text"
        self.state_path = ROOT / op["state_file"]
        self.log_path = ROOT / op["log_file"]

        # Cache
        self.cache = PageCache(self.pages_dir, self.text_dir)

        # State
        self.state = CrawlState(self.state_path)

        # Logger
        self.logger = CrawlLogger(self.log_path)

        # Runtime tracking
        self.fsn_pages: set[str] = set()
        self.page_links: dict[str, list[str]] = {}  # title → related page titles

    # ---- Main entry ----

    def run(self) -> None:
        """Execute the crawl."""
        cfg = self.cfg

        # Print banner
        print("=" * 60)
        print("  FSN Crawler — Moegirlpedia Focused Crawl")
        print("=" * 60)
        print(f"  Seeds:      {cfg['seeds']}")
        print(f"  Max depth:  {cfg['max_depth']}")
        print(f"  Max pages:  {cfg['max_pages']}")
        print(f"  Delay:      {cfg['delay_seconds']}s ± {cfg['jitter_ratio']*100:.0f}%")
        print(f"  Min score:  {cfg['min_relevance_score']}")
        print(f"  Dry run:    {cfg['dry_run']}")
        print(f"  Force:      {cfg['force']}")
        print(f"  Resume:     {self.resume_flag}")
        print(f"  Output:     {self.raw_base}")
        print("=" * 60)
        print()

        self.logger.open()

        try:
            # Load or init state
            if self.resume_flag and self.state.load():
                print("[INFO] Resuming from previous crawl state.")
                self.logger.log("resume", summary=self.state.get_summary())
            else:
                self.state.mark_started(cfg)
                # Seed the queue with seed pages
                seed_items = [
                    {"title": s, "source_page": "", "depth": 0, "display_text": s}
                    for s in cfg["seeds"]
                ]
                self.state.add_to_queue(seed_items)
                self.logger.log("init", seeds=cfg["seeds"], config_summary={
                    "max_depth": cfg["max_depth"],
                    "max_pages": cfg["max_pages"],
                    "min_relevance_score": cfg["min_relevance_score"],
                })

            # BFS loop
            for depth in range(cfg["max_depth"] + 1):
                if self.state.data["pages_crawled"] >= cfg["max_pages"]:
                    print(f"[INFO] Reached max_pages ({cfg['max_pages']}), stopping.")
                    break

                self.state.data["current_depth"] = depth
                batch = self.state.pop_next_batch(cfg["max_pages"])
                if not batch:
                    print(f"[INFO] Queue empty at depth {depth}, stopping.")
                    break

                print(f"\n{'-' * 60}")
                print(f"  Depth {depth}: {len(batch)} pages to crawl")
                print(f"{'-' * 60}")

                for i, item in enumerate(batch):
                    if self.state.data["pages_crawled"] >= cfg["max_pages"]:
                        break
                    self._process_page(item, depth, i + 1, len(batch))

                # Save state after each depth level
                self.state.save()

            # Final summary
            self._print_summary()

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted. Saving state for resume...")
            self.state.save()
            self.logger.log("interrupted", summary=self.state.get_summary())
            print("[INFO] State saved. Re-run with --resume to continue.")
        finally:
            self.logger.close()

    # ---- Process a single page ----

    def _process_page(self, item: dict, depth: int, idx: int, total: int) -> None:
        """Fetch, parse, classify, and archive a single page."""
        cfg = self.cfg
        title = normalize_title(item["title"])
        source_page = item.get("source_page", "")

        print(f"\n  [{idx}/{total}] {title}")
        print(f"        Source: {source_page or '(seed)'}  Depth: {depth}")

        # Check visited
        if self.state.is_visited(title):
            print(f"        [SKIP] Already visited.")
            self.logger.log("skip_visited", title=title)
            return

        # Mark visited early to prevent re-processing
        self.state.mark_visited(title)

        # Dry-run: for depth > 0, just print plan
        if cfg["dry_run"] and depth > 0:
            print(f"        [DRY-RUN] Would fetch this page (depth={depth}).")
            return

        # Check cache (unless --force)
        cached = None if cfg["force"] else self.cache.get(title)
        html = None
        if cached and not cfg["dry_run"]:
            print(f"        [CACHE HIT] Using local cache.")
            self.logger.log("cache_hit", title=title)
            meta = cached["meta"]
            text = cached["text"]
            # Cached pages don't store raw HTML; links from stored metadata
            stored_links = meta.get("_extracted_links", [])
            raw_links = stored_links
        elif cfg["dry_run"]:
            # Dry-run for depth==0 (seed): fetch it to discover links
            print(f"        [DRY-RUN] Fetching seed page for link discovery...")
            self._polite_wait()
            meta, text, html = self._fetch_with_retry(title)
            if meta is None:
                return
            # Cache even in dry-run for seed pages
            self.cache.put(title, meta, text)
            self.logger.log("fetch_seed", title=title, depth=depth)
            raw_links = self._extract_and_store_links(html, title, meta)
        else:
            # Fresh fetch
            self._polite_wait()
            meta, text, html = self._fetch_with_retry(title)
            if meta is None:
                return  # Failed after retries

            # Extract links from HTML and store in meta
            raw_links = self._extract_and_store_links(html, title, meta)

            # Cache it (with stored links)
            self.cache.put(title, meta, text)
            self.logger.log("fetch", title=title, pageid=meta.get("pageid"),
                           html_size=meta.get("html_size", 0), depth=depth,
                           links_found=len(raw_links))

        # Determine if this is an FSN page
        categories = meta.get("categories", [])
        fsn = is_fsn_page(
            title=title,
            categories=categories,
            text=text,
            include_keywords=cfg["include_keywords"],
            threshold=cfg["fsn_page_threshold"],
        )
        if fsn:
            self.fsn_pages.add(title)
            print(f"        [FSN] [OK]  Marked as FSN-related page.")

        # ---- Score and filter links ----
        links_added = 0
        links_excluded = 0
        queued_link_titles: list[str] = []
        if depth < cfg["max_depth"] and raw_links:
            for link in raw_links:
                link_title = normalize_title(link["title"])

                # Quick exclusion
                allowed, reason = is_allowed_page(
                    link_title,
                    allowed_namespaces=cfg["allowed_namespaces"],
                    exclude_keywords=cfg["exclude_keywords"],
                )
                if not allowed:
                    links_excluded += 1
                    self.logger.log("link_excluded",
                                    title=link_title, source=title, reason=reason)
                    continue

                # Relevance scoring
                score, score_reasons = score_page_relevance(
                    title=link_title,
                    categories=[],  # unknown until fetched
                    link_display_text=link.get("display_text", ""),
                    source_page_title=title,
                    source_page_is_fsn=fsn,
                    include_keywords=cfg["include_keywords"],
                    exclude_keywords=cfg["exclude_keywords"],
                )

                if score < cfg["min_relevance_score"]:
                    links_excluded += 1
                    self.logger.log("link_excluded",
                                    title=link_title, source=title,
                                    reason=f"score {score} < threshold {cfg['min_relevance_score']}",
                                    score=score, score_detail=score_reasons)
                    continue

                # Add to queue
                queue_item = {
                    "title": link_title,
                    "source_page": title,
                    "depth": depth + 1,
                    "display_text": link.get("display_text", ""),
                    "score": score,
                }
                self.state.add_to_queue([queue_item])
                links_added += 1
                queued_link_titles.append(link_title)

            self.logger.log("links_processed", source=title,
                           added=links_added, excluded=links_excluded)

        print(f"        Links: +{links_added} queued, -{links_excluded} excluded")
        related = queued_link_titles[:20]

        # ---- Save raw data ----
        save_raw_page(
            title=title,
            meta=meta,
            text=text,
            pages_dir=self.pages_dir,
            text_dir=self.text_dir,
        )

        # ---- Classify and archive ----
        cat, cat_reason = classify_page(
            title=title,
            text=text,
            metadata=meta,
            categories=categories,
            category_rules=cfg.get("category_rules"),
        )
        print(f"        Category: {cat}  (scores: {cat_reason.get('scores', {})})")

        # Track related pages for cross-reference
        self.page_links[title] = related

        save_markdown_page(
            title=title,
            text=text,
            category=cat,
            meta=meta,
            crawl_depth=depth,
            related_pages=related,
            source="moegirl",
            sources_dir=self.sources_dir,
            wiki_dir=self.wiki_base,
            category_reason=cat_reason,
        )
        self.logger.log("classified", title=title, category=cat, reason=cat_reason)

        # Save state periodically
        self.state.save()

    # ---- Link extraction helper ----

    def _extract_and_store_links(self, html: str, title: str, meta: dict) -> list[dict]:
        """Extract links from HTML and store them in meta for future cache hits."""
        try:
            raw_links = extract_links(html, title)
        except Exception as e:
            print(f"        [WARN] Link extraction failed: {e}")
            raw_links = []

        # Store in meta so cache hits can re-use without HTML
        meta["_extracted_links"] = raw_links
        return raw_links

    # ---- Fetch with retry ----

    def _fetch_with_retry(self, title: str) -> tuple:
        """Fetch a page with exponential backoff retry.

        Returns (meta, text, html) or (None, None, None) if all retries fail.
        """
        cfg = self.cfg
        last_error = None

        for attempt in range(1, cfg["max_retries"] + 1):
            try:
                result = scrape_page(title)
                return (result["meta"], result["text"], result.get("html", ""))
            except Exception as e:
                last_error = e
                print(f"        [RETRY {attempt}/{cfg['max_retries']}] {e}")
                self.logger.log("fetch_error", title=title,
                               attempt=attempt, error=str(e))

                if attempt < cfg["max_retries"]:
                    delay = retry_delay(attempt, cfg["retry_base_delay"])
                    print(f"        Waiting {delay:.0f}s before retry...")
                    time.sleep(delay)

        print(f"        [FAILED] All retries exhausted for: {title}")
        self.state.record_error({
            "title": title,
            "error": str(last_error),
            "retries": cfg["max_retries"],
        })
        return (None, None, None)

    # ---- Delay ----

    def _polite_wait(self) -> None:
        """Wait between requests with jitter."""
        cfg = self.cfg
        polite_delay(cfg["delay_seconds"], cfg["jitter_ratio"])

    # ---- Summary ----

    def _print_summary(self) -> None:
        """Print final crawl summary."""
        summary = self.state.get_summary()
        print(f"\n{'=' * 60}")
        print(f"  Crawl Complete")
        print(f"{'=' * 60}")
        print(f"  Pages crawled:  {summary['pages_crawled']}")
        print(f"  Pages visited:  {summary['pages_visited']}")
        print(f"  Queue remaining: {summary['queue_size']}")
        print(f"  Max depth:      {summary['current_depth']}")
        print(f"  Errors:         {summary['error_count']}")
        print(f"  FSN pages:      {len(self.fsn_pages)}")
        print(f"  Raw data:       {self.pages_dir}")
        print(f"  Text data:      {self.text_dir}")
        print(f"  Wiki pages:     {self.wiki_base}")
        print(f"  Log:            {self.log_path}")
        print(f"  State:          {self.state_path}")
        print(f"{'=' * 60}")

        self.logger.log("complete", summary=summary,
                       fsn_page_count=len(self.fsn_pages))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="FSN-focused controlled crawler for Moegirlpedia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/crawl_fsn.py --seed "间桐樱" --max-depth 1 --max-pages 10 --delay 5
  python scripts/crawl_fsn.py --seeds config/fsn_seeds.txt --max-depth 2 --max-pages 80
  python scripts/crawl_fsn.py --dry-run --seed "间桐樱" --max-depth 1
  python scripts/crawl_fsn.py --seed "间桐樱" --resume
        """,
    )

    # Seed pages
    seed_group = p.add_mutually_exclusive_group()
    seed_group.add_argument("--seed", type=str, default=None,
                           help="Single seed page title.")
    seed_group.add_argument("--seeds", type=str, default=None,
                           help="Path to file with seed page titles (one per line).")

    # Crawl boundaries
    p.add_argument("--max-depth", type=int, default=None,
                  help="Maximum link expansion depth (default from config).")
    p.add_argument("--max-pages", type=int, default=None,
                  help="Maximum number of pages to crawl (default from config).")
    p.add_argument("--min-score", type=int, default=None,
                  help="Minimum relevance score for linked pages.")

    # Politeness
    p.add_argument("--delay", type=float, default=None,
                  help="Delay between requests in seconds.")
    p.add_argument("--jitter", type=float, default=None,
                  help="Jitter ratio for delay (0.0 - 1.0).")
    p.add_argument("--max-retries", type=int, default=None,
                  help="Maximum retries per failed request.")

    # Operational modes
    p.add_argument("--resume", action="store_true", default=False,
                  help="Resume from a previous interrupted crawl.")
    p.add_argument("--dry-run", action="store_true", default=False,
                  help="Print crawl plan without making real requests.")
    p.add_argument("--force", action="store_true", default=False,
                  help="Ignore local cache and re-fetch all pages.")

    # Config
    p.add_argument("--config", type=str, default=None,
                  help="Path to YAML config file (default: config/fsn_crawl.yaml).")
    p.add_argument("--output-dir", type=str, default=None,
                  help="Base output directory (overrides config paths).")
    p.add_argument("--include-keywords", type=str, default=None,
                  help="Path to include keywords file.")
    p.add_argument("--exclude-keywords", type=str, default=None,
                  help="Path to exclude keywords file.")

    return p


def main():
    parser = build_argparser()
    args = parser.parse_args()

    # Validate: need seeds
    if not args.seed and not args.seeds and not args.resume:
        # Check if config file has seeds
        config_path = args.config or str(ROOT / "config" / "fsn_crawl.yaml")
        if Path(config_path).exists():
            pass  # Config will provide seeds
        else:
            print("[ERROR] No seed specified. Use --seed, --seeds, or --resume.",
                  file=sys.stderr)
            parser.print_help()
            sys.exit(1)

    # Load merged config
    cfg = load_config(args)

    # Validate seeds
    if not cfg["seeds"] and not args.resume:
        print("[ERROR] No seed pages configured.", file=sys.stderr)
        sys.exit(1)

    # Create crawler and run
    crawler = FSNCrawler(cfg, resume=args.resume)
    crawler.run()


if __name__ == "__main__":
    main()
