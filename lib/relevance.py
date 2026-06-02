#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relevance.py — Rule-based relevance scoring for FSN-related pages.

No LLM dependency — all scoring is based on transparent, configurable rules.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Default keyword sets (overridable via config)
# ---------------------------------------------------------------------------

DEFAULT_INCLUDE_KEYWORDS: list[str] = [
    # Works / Series
    "Fate", "Fate/stay night", "Fate/Stay Night", "Fate/Zero",
    "Fate/hollow ataraxia", "Fate/EXTRA", "Fate/Grand Order",
    "Fate/Apocrypha", "Fate/strange Fake", "Fate/Prototype",
    "TYPE-MOON", "型月", "TYPE MOON",
    "圣杯战争", "Holy Grail War",
    "月姬", "魔法使之夜", "空之境界",
    "Notes", "DDD", "Canaan",

    # Core FSN character names
    "卫宫士郎", "卫宫", "士郎", "EMIYA", "Archer",
    "Saber", "远坂凛", "间桐樱", "伊莉雅", "伊莉雅斯菲尔",
    "Rider", "Lancer", "Berserker", "Caster", "Assassin",
    "Gilgamesh", "吉尔伽美什", "言峰绮礼", "藤村大河",
    "间桐慎二", "间桐脏砚", "间桐雁夜", "远坂时臣",
    "美缀绫子", "柳洞一成", "葛木宗一郎", "Caster",
    "佐佐木小次郎", "库丘林", "美杜莎",
    "赫拉克勒斯", "海格力斯",

    # FSN concepts
    "从者", "Servant", "御主", "Master", "令咒", "Command Spell",
    "宝具", "Noble Phantasm", "职阶", "Class",
    "根源", "魔术", "魔术师", "魔术回路", "Magic Circuit",
    "圣杯", "Holy Grail", "大圣杯", "小圣杯",
    "无限剑制", "Unlimited Blade Works",
    "王之财宝", "Gate of Babylon",
    "天之锁", "天之杯", "Heaven's Feel",
    "理想乡", "Avalon", "誓约胜利之剑", "Excalibur",

    # Locations / Factions
    "冬木市", "冬木", "穗群原学园", "远坂家", "间桐家",
    "爱因兹贝伦", "教会", "魔术协会", "时钟塔",
    "柳洞寺", "卫宫邸", "教会",

    # Category markers (used in relevance scoring)
    "Fate系列", "TYPE-MOON作品", "型月作品",
    "Fate/stay night角色", "Fate系列角色",
]


DEFAULT_EXCLUDE_KEYWORDS: list[str] = [
    # Wiki meta / help
    "帮助", "Help", "模板", "Template", "文件", "File",
    "分类", "Category", "用户", "User", "讨论", "Talk",
    "萌娘百科", "特殊", "Special", "MediaWiki",

    # Disambiguation / list pages
    "消歧义", "disambiguation", "列表", "list of",
    "导航", "Navigation",

    # Maintenance / policy
    "版权", "Copyright", "隐私", "Privacy", "免责",
    "方针", "Policy", "指引", "Guideline",
    "沙盒", "Sandbox", "待删除", "删除",
    "存废", "快速删除", "侵权",

    # Unrelated works (short list — expand as needed)
    # These help avoid cross-contamination from non-TYPE-MOON works
    # "原神", "崩坏", etc. would go here if needed
]


# ---------------------------------------------------------------------------
# Relevance scorer
# ---------------------------------------------------------------------------

def _keyword_score(text: str, keywords: list[str]) -> int:
    """Count keyword matches in text (case-insensitive for ASCII, exact for CJK)."""
    score = 0
    text_lower = text.lower()
    for kw in keywords:
        # For ASCII keywords, do case-insensitive match
        if kw.isascii():
            if kw.lower() in text_lower:
                score += 1
        else:
            if kw in text:
                score += 1
    return score


def _compile_score(
    *,
    title: str,
    categories: list[str],
    link_display_text: str,
    source_page_title: str,
    source_page_is_fsn: bool,
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> tuple[int, dict]:
    """Core scoring logic — returns (score, reason_dict)."""

    reasons: dict[str, int] = {}
    exclude_reasons: list[str] = []

    # --- 0. Exclusion check first ---
    exclude_hits = _keyword_score(title, exclude_keywords)
    if exclude_hits > 0:
        exclude_reasons.append(f"title matched {exclude_hits} exclude keywords")
        return (-100, {"excluded": True, "exclude_reasons": exclude_reasons})

    # Also check display text for exclusion
    exclude_hits_display = _keyword_score(link_display_text, exclude_keywords)
    if exclude_hits_display > 0:
        exclude_reasons.append(f"display_text matched {exclude_hits_display} exclude keywords")
        return (-100, {"excluded": True, "exclude_reasons": exclude_reasons})

    score = 0

    # --- 1. Title keyword match (high weight) ---
    title_kw_score = _keyword_score(title, include_keywords)
    reasons["title_keywords"] = title_kw_score
    score += title_kw_score * 5

    # --- 2. Display text keyword match ---
    display_kw_score = _keyword_score(link_display_text, include_keywords)
    reasons["display_text_keywords"] = display_kw_score
    score += display_kw_score * 3

    # --- 3. Page category match (high weight) ---
    cat_text = " ".join(categories)
    cat_score = _keyword_score(cat_text, include_keywords)
    reasons["category_keywords"] = cat_score
    score += cat_score * 6

    # Specific high-value category checks
    high_value_cats = [
        "Fate系列", "TYPE-MOON作品", "型月作品", "Fate",
        "Fate/stay night", "Fate/stay night角色", "Fate系列角色",
    ]
    for cat in categories:
        for hvc in high_value_cats:
            if hvc.lower() in cat.lower():
                reasons.setdefault("high_value_category", 0)
                reasons["high_value_category"] += 10
                score += 10

    # --- 4. Source page bonus ---
    if source_page_is_fsn:
        reasons["source_is_fsn"] = 8
        score += 8

    # Source page title keyword bonus
    source_bonus = _keyword_score(source_page_title, include_keywords) * 2
    if source_bonus:
        reasons["source_page_bonus"] = source_bonus
        score += source_bonus

    # --- 5. Penalties ---
    # Titles that are very short and generic (likely disambiguation remnants)
    if len(title) <= 2 and not any(kw in title for kw in include_keywords):
        reasons["short_generic_penalty"] = -5
        score -= 5

    reasons["_total"] = score
    return (score, reasons)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_page_relevance(
    *,
    title: str,
    categories: Optional[list[str]] = None,
    link_display_text: str = "",
    source_page_title: str = "",
    source_page_is_fsn: bool = False,
    include_keywords: Optional[list[str]] = None,
    exclude_keywords: Optional[list[str]] = None,
) -> tuple[int, dict]:
    """Score a candidate page's relevance to FSN.

    Parameters
    ----------
    title : str
        Normalised page title.
    categories : list[str] or None
        Page categories (from metadata, if already fetched).
    link_display_text : str
        The anchor text used in the link to this page.
    source_page_title : str
        Title of the page where this link was found.
    source_page_is_fsn : bool
        Whether the source page itself has been classified as FSN-related.
    include_keywords : list[str] or None
        Keywords that signal FSN relevance.
    exclude_keywords : list[str] or None
        Keywords that signal exclusion.

    Returns
    -------
    (score, reasons)
        score : int — higher = more relevant. -100 means excluded.
        reasons : dict — breakdown of scoring factors.
    """
    if include_keywords is None:
        include_keywords = DEFAULT_INCLUDE_KEYWORDS
    if exclude_keywords is None:
        exclude_keywords = DEFAULT_EXCLUDE_KEYWORDS
    if categories is None:
        categories = []

    return _compile_score(
        title=title,
        categories=categories,
        link_display_text=link_display_text,
        source_page_title=source_page_title,
        source_page_is_fsn=source_page_is_fsn,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
    )


def is_allowed_page(
    title: str,
    *,
    allowed_namespaces: Optional[list[str]] = None,
    exclude_keywords: Optional[list[str]] = None,
) -> tuple[bool, str]:
    """Quick check: is this page allowed for crawling?

    Returns (is_allowed, reason).
    """
    from .link_extractor import extract_namespace, normalize_title

    normalized = normalize_title(title)

    # Namespace check
    ns = extract_namespace(normalized)
    if ns:
        if allowed_namespaces and ns not in allowed_namespaces:
            return False, f"namespace '{ns}' not in allowed list"
        if not allowed_namespaces and ns != "":
            return False, f"namespace '{ns}' is not mainspace"

    # Exclude-keyword check on title
    if exclude_keywords is None:
        exclude_keywords = DEFAULT_EXCLUDE_KEYWORDS

    for kw in exclude_keywords:
        if kw.lower() in normalized.lower():
            return False, f"title contains exclude keyword: '{kw}'"

    return True, "allowed"


def is_fsn_page(
    *,
    title: str,
    categories: Optional[list[str]] = None,
    text: Optional[str] = None,
    include_keywords: Optional[list[str]] = None,
    threshold: int = 15,
) -> bool:
    """Determine if a page is FSN-related based on its content.

    This is used to mark source pages as FSN, which then boosts
    the relevance of their outgoing links.
    """
    if include_keywords is None:
        include_keywords = DEFAULT_INCLUDE_KEYWORDS

    score = 0
    score += _keyword_score(title, include_keywords) * 5

    if categories:
        cat_text = " ".join(categories)
        score += _keyword_score(cat_text, include_keywords) * 3

    if text:
        # Sample text to limit scoring time on long pages
        sample = text[:5000]
        score += _keyword_score(sample, include_keywords)

    return score >= threshold
