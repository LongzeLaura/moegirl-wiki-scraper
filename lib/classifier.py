#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classifier.py — Classify scraped pages into FSN setting categories.

Uses heuristic keyword matching — no LLM dependency.
Categories: characters, world, locations, factions, items, plot-arcs, uncategorized.
"""

import re

# ---------------------------------------------------------------------------
# Category rules
# ---------------------------------------------------------------------------

CATEGORY_RULES: dict[str, dict] = {
    "characters": {
        "label": "角色",
        "keywords": [
            "角色", "人物", "声优", "身高", "体重", "生日", "血型",
            "从者", "Servant", "御主", "Master", "萌点", "三围",
            "发色", "瞳色", "星座", "出身", "个人状态",
            "登场角色", "登场人物", "女主角", "男主角",
            "印象色", "特技", "所好之物", "不擅长",
            "天敌", "魔术属性", "亲属",
            # English patterns for meta
            "character", "servant", "master",
        ],
    },
    "world": {
        "label": "世界观/设定",
        "keywords": [
            "圣杯战争", "Holy Grail War", "魔术", "令咒",
            "Command Spell", "职阶", "Class", "从者系统",
            "根源", "魔术师", "魔术回路", "Magic Circuit",
            "宝具", "Noble Phantasm", "固有结界",
            "Reality Marble", "魔术协会", "Mage's Association",
            "概念", "设定", "世界", "法则", "属性",
            "起源", "抑制力", "Counter Force",
            "魔法", "魔术", "神秘", "礼装",
            "刻印", "魔术刻印", "契约",
        ],
    },
    "locations": {
        "label": "地点",
        "keywords": [
            "地点", "城市", "学校", "教会", "宅邸", "冬木",
            "穗群原学园", "柳洞寺", "卫宫邸", "远坂邸",
            "间桐邸", "爱因兹贝伦城", "教会", "大桥",
            "公园", "商店街", "新都", "深山町",
            "地图", "位置", "地区", "建筑",
        ],
    },
    "factions": {
        "label": "组织/阵营",
        "keywords": [
            "组织", "阵营", "协会", "教会", "家族",
            "魔术协会", "时钟塔", "阿特拉斯院",
            "彷徨海", "圣堂教会", "埋葬机关",
            "远坂家", "间桐家", "爱因兹贝伦",
            "穗群原", "弓道部", "学生会",
            "faction", "organization",
        ],
    },
    "items": {
        "label": "道具/宝具",
        "keywords": [
            "宝具", "Noble Phantasm", "道具", "礼装", "武器",
            "剑", "枪", "弓", "盾", "魔术礼装",
            "圣杯", "Holy Grail", "令咒", "Command Spell",
            "武器", "装备", "武装",
        ],
    },
    "plot-arcs": {
        "label": "剧情/路线",
        "keywords": [
            "路线", "剧情", "结局", "事件", "章节",
            "Fate", "Unlimited Blade Works", "Heaven's Feel",
            "无限剑制", "天之杯", "故事", "情节",
            "route", "plot", "story", "arc",
        ],
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_page(
    title: str,
    text: str,
    metadata: dict | None = None,
    categories: list[str] | None = None,
    category_rules: dict | None = None,
) -> tuple[str, dict]:
    """Classify a page into an FSN setting category.

    Parameters
    ----------
    title : str
        Page title.
    text : str
        Extracted plain text of the page.
    metadata : dict or None
        Page metadata (categories, etc.).
    categories : list[str] or None
        Page categories.
    category_rules : dict or None
        Override the default CATEGORY_RULES.

    Returns
    -------
    (category_key, reason_dict)
        category_key: one of "characters", "world", "locations", "factions",
                      "items", "plot-arcs", "uncategorized".
        reason_dict: {category: score, ...} showing why.
    """
    if category_rules is None:
        category_rules = CATEGORY_RULES

    if categories is None and metadata:
        categories = metadata.get("categories", [])

    # Build search text: title (×3 weight) + first 10KB of text + categories
    search_text = f"{title} {title} {title} {text[:10000]} {' '.join(categories or [])}"

    scores: dict[str, int] = {}
    for cat_key, rule in category_rules.items():
        kw_score = 0
        for kw in rule["keywords"]:
            if kw.lower() in search_text.lower():
                kw_score += 1
        scores[cat_key] = kw_score

    # Find best category
    best_cat = "uncategorized"
    best_score = 0
    for cat_key, score in scores.items():
        if score > best_score:
            best_score = score
            best_cat = cat_key

    # Only classify if we have at least some signal
    if best_score < 2:
        best_cat = "uncategorized"

    reason = {
        "scores": scores,
        "best_category": best_cat,
        "best_score": best_score,
    }
    if best_cat == "uncategorized":
        reason["reason"] = "no category reached minimum keyword threshold"

    return best_cat, reason
