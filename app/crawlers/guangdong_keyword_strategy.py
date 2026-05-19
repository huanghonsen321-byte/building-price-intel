"""Guangdong keyword strategy — classify, filter, and validate keywords.

This module provides:
1. Core / Combination / Excluded keyword classification
2. Negative keyword filtering (e.g., "盘岭" is a place name, not scaffolding)
3. Context-aware relevance checks for ambiguous keywords
4. Production-safe keyword lists for the Guangdong plan

Based on keyword coverage scan results:
- "盘扣" alone returns mostly "盘岭" place-name false positives
- "脚手架" has only 27 real hits
- "盘扣式脚手架" is the most precise keyword for scaffolding

Scan report: app/crawlers/output/guangdong_keyword_coverage_20260519_220626.json
"""

from __future__ import annotations

from dataclasses import dataclass, field

# === 1. CORE KEYWORDS — precise, production-ready ===
CORE_KEYWORDS = [
    "脚手架",
    "盘扣式脚手架",
    "扣件式脚手架",
    "钢管脚手架",
    "模板脚手架",
    "脚手架搭拆",
    "钢管扣件租赁",
    "周转材料租赁",
    "附着式升降脚手架",
    "盘扣架租赁",
    "钢管租赁",
    "扣件租赁",
]

# === 2. COMBINATION KEYWORDS — need secondary filtering ===
COMBINATION_KEYWORDS = [
    ("盘扣", "脚手架"),
    ("盘扣", "租赁"),
    ("盘扣", "支撑"),
    ("钢管", "租赁"),
    ("钢管", "扣件"),
    ("模板", "支撑"),
    ("模板", "脚手架"),
    ("周转材料", "租赁"),
]

# === 3. EXCLUDED SINGLE KEYWORDS — high noise, not for solo use ===
EXCLUDED_SINGLE_KEYWORDS = [
    "盘扣",   # Mostly "盘岭" place name
    "模板",   # Too broad, hits all construction projects
    "工程材料",  # Generic term, hits everything
    "租赁",   # Hits housing, equipment, vehicles...
    "建筑材料",  # Too broad
    "支架",   # Hits solar panels, medical, furniture...
]

# === 4. NEGATIVE KEYWORDS — if present in title, likely false positive ===
NEGATIVE_KEYWORDS = [
    "盘岭",   # Place name, NOT scaffolding
    "盘龙",   # Place name
    "盘古",   # Place name / brand
    "楼盘",   # Real estate term
    "沙盘",   # Real estate model
    "开盘",   # Real estate / finance
    "收盘",   # Finance
    "椎间盘",  # Medical (lumbar disc)
    "股盘",   # Finance
]

# === 5. REQUIRED CONTEXT FOR AMBIGUOUS KEYWORDS ===
# If an ambiguous keyword appears, at least one of these must also appear
AMBIGUOUS_KEYWORD_CONTEXT = {
    "盘扣": [
        "脚手架", "租赁", "支撑", "钢管", "扣件",
        "模板", "周转材料", "架体", "搭拆",
    ],
}


@dataclass
class KeywordClassification:
    """Classification result for a keyword."""
    keyword: str
    category: str  # "core", "combination", "excluded", "unknown"
    is_production_safe: bool
    needs_secondary_filter: bool
    false_positive_risk: str  # "low", "medium", "high"


def classify_guangdong_keyword(keyword: str) -> str:
    """Classify a keyword into core / combination / excluded / unknown."""
    if keyword in CORE_KEYWORDS:
        return "core"
    if keyword in EXCLUDED_SINGLE_KEYWORDS:
        return "excluded"
    # Check if it's part of a combination pair
    for a, b in COMBINATION_KEYWORDS:
        if keyword == a or keyword == b:
            return "combination"
    return "unknown"


def is_negative_hit(title: str, text: str = "") -> bool:
    """Check if the title/text contains a negative keyword (false positive)."""
    combined = f"{title} {text}".lower()
    return any(neg in combined for neg in NEGATIVE_KEYWORDS)


def is_relevant_guangdong_hit(keyword: str, title: str, text: str = "") -> bool:
    """Check if a search result is relevant to scaffolding/construction materials.

    Rules:
    1. If any negative keyword is in title/text, it's a false positive.
    2. If the keyword is ambiguous (e.g. "盘扣"), check for required context words.
    3. Core keywords are considered relevant by default.
    """
    # Rule 1: Negative hit check
    if is_negative_hit(title, text):
        return False

    # Rule 2: Ambiguous keyword context check
    if keyword in AMBIGUOUS_KEYWORD_CONTEXT:
        required_context = AMBIGUOUS_KEYWORD_CONTEXT[keyword]
        combined = f"{title} {text}"
        if not any(ctx in combined for ctx in required_context):
            return False

    return True


def get_guangdong_production_keywords() -> list[str]:
    """Return the production-safe keywords for Guangdong plan."""
    return list(CORE_KEYWORDS)


def get_guangdong_combination_queries() -> list[dict]:
    """Return combination queries as structured dicts."""
    return [
        {"primary": a, "secondary": b, "query": f"{a} {b}"}
        for a, b in COMBINATION_KEYWORDS
    ]


def should_include_result(keyword: str, title: str, text: str = "") -> bool:
    """Decide whether to include a search result for the given keyword.

    Returns True if the result passes all filters.
    """
    category = classify_guangdong_keyword(keyword)

    # Excluded keywords are not production-safe
    if category == "excluded":
        return False

    # Check negative keywords
    if is_negative_hit(title, text):
        return False

    # Check relevance
    if not is_relevant_guangdong_hit(keyword, title, text):
        return False

    return True


def get_all_keyword_info() -> dict:
    """Return a summary of the keyword strategy."""
    return {
        "core_keywords": CORE_KEYWORDS,
        "combination_keywords": COMBINATION_KEYWORDS,
        "excluded_keywords": EXCLUDED_SINGLE_KEYWORDS,
        "negative_keywords": NEGATIVE_KEYWORDS,
        "ambiguous_context": AMBIGUOUS_KEYWORD_CONTEXT,
        "total_core": len(CORE_KEYWORDS),
        "total_combination": len(COMBINATION_KEYWORDS),
        "total_excluded": len(EXCLUDED_SINGLE_KEYWORDS),
    }
