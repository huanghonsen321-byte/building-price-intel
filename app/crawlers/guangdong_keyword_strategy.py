"""Guangdong keyword strategy — two-layer (core + discovery) classification.

Layer 1 (Core): Precise keywords that enter production directly.
Layer 2 (Discovery): Broad keywords that need secondary filtering before inclusion.

Based on scan results:
- "盘扣" alone returns 320 hits, 98% are "盘岭" place-name false positives
- "钢管" returns 8 real hits but needs context filtering

Scan report: docs/guangdong_keyword_coverage.md
"""

from __future__ import annotations

# === LAYER 1: CORE KEYWORDS — precise, production-ready ===
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

# === LAYER 2: DISCOVERY KEYWORDS — need secondary filtering ===
DISCOVERY_KEYWORDS = [
    "钢管",
    "盘扣",
    "扣件",
    "模板",
    "支架",
    "周转材料",
    "安全网",
    "顶托",
    "钢跳板",
    "铝模",
    "木方",
]

# === NEGATIVE KEYWORDS — if present in title, likely false positive ===
NEGATIVE_KEYWORDS = [
    "盘岭",
    "盘龙",
    "盘古",
    "楼盘",
    "沙盘",
    "开盘",
    "收盘",
    "椎间盘",
    "股盘",
    "地名盘",
]

# === SECONDARY FILTER CONTEXT WORDS ===
# For discovery keywords, title/text must contain at least one of these
DISCOVERY_CONTEXT_WORDS = [
    "脚手架",
    "租赁",
    "支撑",
    "钢管",
    "扣件",
    "模板",
    "周转材料",
    "架体",
    "搭拆",
    "工程",
    "采购",
    "招标",
    "中标",
    "施工",
]

# === EXCLUDED KEYWORDS — too broad, only for offline exploration ===
EXCLUDED_KEYWORDS = [
    "模板工程",
    "工程材料",
    "建筑材料",
    "租赁",
    "工程",
]


def classify_keyword(keyword: str) -> str:
    """Classify a keyword into 'core', 'discovery', 'excluded', or 'unknown'."""
    if keyword in CORE_KEYWORDS:
        return "core"
    if keyword in DISCOVERY_KEYWORDS:
        return "discovery"
    if keyword in EXCLUDED_KEYWORDS:
        return "excluded"
    return "unknown"


def is_negative_hit(text: str) -> bool:
    """Check if text contains a negative keyword (false positive indicator)."""
    lower = text.lower()
    return any(neg in lower for neg in NEGATIVE_KEYWORDS)


def should_include_discovery_result(keyword: str, title: str, text: str = "") -> bool:
    """Check if a discovery keyword hit passes secondary filtering.

    Rules:
    1. No negative keywords in title/text
    2. At least one discovery context word appears in title or text
    """
    combined = f"{title} {text}".lower()

    # Rule 1: Negative hit check
    if is_negative_hit(combined):
        return False

    # Rule 2: Must contain at least one context word other than the broad
    # discovery keyword itself. For example, a title that is only "钢管" is
    # not enough; "钢管租赁项目" or "钢管采购工程" is acceptable.
    context_words = [ctx for ctx in DISCOVERY_CONTEXT_WORDS if ctx != keyword]
    if not any(ctx in combined for ctx in context_words):
        return False

    return True


def should_include_result(keyword: str, title: str, text: str = "") -> bool:
    """Decide whether to include a search result.

    - Core keywords: only negative filtering applied
    - Discovery keywords: negative + context filtering applied
    """
    category = classify_keyword(keyword)

    if category == "excluded":
        return False

    if category == "discovery":
        return should_include_discovery_result(keyword, title, text)

    # For core keywords, just check negatives
    combined = f"{title} {text}"
    if is_negative_hit(combined):
        return False

    return True


def get_core_keywords() -> list[str]:
    """Return the core production keywords."""
    return list(CORE_KEYWORDS)


def get_discovery_keywords() -> list[str]:
    """Return the discovery keywords (need secondary filtering)."""
    return list(DISCOVERY_KEYWORDS)


def get_guangdong_plan_keywords(max_keywords: int = 0) -> list[str]:
    """Return Guangdong plan keywords with core first and discovery fallback.

    The crawler runner executes keywords in order and stops a source once a
    keyword produces saved results. If a small max_keywords cap only takes
    core keywords, the plan can miss real Guangdong hits such as "钢管".
    Reserve a small tail for discovery keywords while keeping core keywords
    first.
    """
    ordered = CORE_KEYWORDS + DISCOVERY_KEYWORDS
    if max_keywords <= 0 or max_keywords >= len(ordered):
        return list(ordered)
    if max_keywords <= 4:
        return CORE_KEYWORDS[:max_keywords]
    discovery_slots = min(len(DISCOVERY_KEYWORDS), max(1, max_keywords // 4))
    core_slots = max_keywords - discovery_slots
    return CORE_KEYWORDS[:core_slots] + DISCOVERY_KEYWORDS[:discovery_slots]


def get_all_keywords() -> list[str]:
    """Return all keywords (core + discovery + excluded)."""
    return CORE_KEYWORDS + DISCOVERY_KEYWORDS + EXCLUDED_KEYWORDS


def get_all_keyword_info() -> dict:
    """Return a summary of the keyword strategy."""
    return {
        "core_keywords": CORE_KEYWORDS,
        "discovery_keywords": DISCOVERY_KEYWORDS,
        "excluded_keywords": EXCLUDED_KEYWORDS,
        "negative_keywords": NEGATIVE_KEYWORDS,
        "discovery_context_words": DISCOVERY_CONTEXT_WORDS,
        "total_core": len(CORE_KEYWORDS),
        "total_discovery": len(DISCOVERY_KEYWORDS),
        "total_excluded": len(EXCLUDED_KEYWORDS),
        "total_negative": len(NEGATIVE_KEYWORDS),
    }