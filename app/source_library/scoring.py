"""Source library scoring — compute reliability scores for data sources."""

from __future__ import annotations

from app.source_library.schemas import SourceEntry


def compute_reliability_score(source: SourceEntry) -> float:
    """Compute a 0.0–1.0 reliability score based on source metadata.

    Scoring factors:
    - parser_status = parser_ready: +0.4
    - public_api_found: +0.2
    - public_page_reachable: +0.1
    - enabled and not blocked: +0.1
    - has parser_name: +0.1
    - source_level = national: +0.05
    - has keywords: +0.05
    Penalty:
    - blocked or needs_browser: -0.2
    - requires_manual_review: -0.1
    """
    score = 0.0

    if source.parser_status == "parser_ready":
        score += 0.4
    elif source.parser_status == "fixture_ready":
        score += 0.2

    if source.public_api_found:
        score += 0.2
    if source.public_page_reachable:
        score += 0.1
    if source.enabled and source.parser_status not in ("blocked", "deprecated"):
        score += 0.1
    if source.parser_name:
        score += 0.1
    if source.source_level == "national":
        score += 0.05
    if source.keywords:
        score += 0.05

    if source.parser_status in ("blocked", "needs_browser"):
        score -= 0.2
    if source.requires_manual_review:
        score -= 0.1

    return max(0.0, min(1.0, score))


def score_all_sources(sources: list[SourceEntry]) -> list[tuple[SourceEntry, float]]:
    """Score all sources and return sorted by score descending."""
    scored = [(s, compute_reliability_score(s)) for s in sources]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
