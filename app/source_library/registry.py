"""Source library registry — load, query, and manage data source entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.source_library.schemas import (
    SourceEntry,
    SourceLibraryStats,
    SourceQuery,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "crawlers" / "config"
LIBRARY_PATH = CONFIG_DIR / "source_library_national.json"
KEYWORD_LIBRARY_PATH = CONFIG_DIR / "keyword_library.json"

_cache: dict | None = None
_entries_cache: list[SourceEntry] | None = None


def _flatten_sources(data: dict) -> list[SourceEntry]:
    """Flatten all source categories into a single list of SourceEntry objects."""
    entries: list[SourceEntry] = []
    index = 0

    def _add(source: dict, category: str = "") -> None:
        nonlocal index
        index += 1
        entry = SourceEntry(
            name=source.get("name", f"source-{index}"),
            url=source.get("url", ""),
            domain=source.get("domain", ""),
            source_level=source.get("source_level", "national"),
            source_type=source.get("source_type", "bid"),
            acquisition_method=source.get("acquisition_method", "html_list_page"),
            keywords=source.get("keywords", []),
            parser_name=source.get("parser_name"),
            enabled=source.get("enabled", False),
            parser_status=source.get("parser_status", "not_started"),
            requires_browser=source.get("requires_browser", False),
            requires_manual_review=source.get("requires_manual_review", False),
            rate_limit_seconds=source.get("rate_limit_seconds", 3),
            reliability_score=source.get("reliability_score", 0.0),
            province=source.get("province"),
            city=source.get("city"),
            district=source.get("district"),
            country=source.get("country", "CN"),
            public_api_found=source.get("public_api_found", False),
            public_page_reachable=source.get("public_page_reachable", False),
            last_success_at=source.get("last_success_at"),
            last_failed_at=source.get("last_failed_at"),
            last_blocked_reason=source.get("last_blocked_reason"),
            tags=source.get("tags", []),
            notes=source.get("notes", ""),
            category=category,
        )
        entries.append(entry)

    for cat_key, cat_label in [
        ("national_sources", "national"),
        ("guangdong_provincial_sources", "guangdong_province"),
        ("guangdong_city_sources", "guangdong_city"),
        ("national_province_sources", "national_province"),
        ("price_sources", "price"),
        ("manual_import_sources", "manual"),
    ]:
        for source in data.get(cat_key, []):
            _add(source, cat_label)

    return entries


def load_source_library(force: bool = False) -> dict:
    """Load source library from JSON file."""
    global _cache, _entries_cache
    if _cache is not None and _entries_cache is not None and not force:
        return _cache
    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    _cache = data
    _entries_cache = _flatten_sources(data)
    return data


def load_keyword_library() -> dict:
    return json.loads(KEYWORD_LIBRARY_PATH.read_text(encoding="utf-8"))


def _entries() -> list[SourceEntry]:
    global _entries_cache
    if _entries_cache is None:
        load_source_library()
    return _entries_cache or []


def get_sources(query: SourceQuery | None = None) -> list[SourceEntry]:
    """Get sources filtered by query parameters."""
    all_entries = _entries()
    if query is None:
        return all_entries

    def _match(e: SourceEntry) -> bool:
        if query.province and e.province != query.province:
            return False
        if query.city and e.city != query.city:
            return False
        if query.source_level and e.source_level != query.source_level:
            return False
        if query.source_type and e.source_type != query.source_type:
            return False
        if query.acquisition_method and e.acquisition_method != query.acquisition_method:
            return False
        if query.parser_status and e.parser_status != query.parser_status:
            return False
        if query.enabled is not None and e.enabled != query.enabled:
            return False
        if query.keyword:
            kw = query.keyword
            if kw not in e.keywords and kw not in e.name:
                return False
        if query.tag and query.tag not in e.tags:
            return False
        return True

    filtered = [e for e in all_entries if _match(e)]
    return filtered[query.offset : query.offset + query.limit]


def get_source(name_or_index: str | int) -> SourceEntry | None:
    """Get a single source by name (exact match) or 1-based index."""
    all_entries = _entries()
    if isinstance(name_or_index, int):
        idx = name_or_index - 1
        return all_entries[idx] if 0 <= idx < len(all_entries) else None
    for e in all_entries:
        if e.name == name_or_index:
            return e
    return None


def get_source_count(query: SourceQuery | None = None) -> int:
    return len(get_sources(query))


def get_stats() -> SourceLibraryStats:
    """Compute aggregate statistics."""
    all_entries = _entries()

    stats = SourceLibraryStats()
    stats.total_sources = len(all_entries)

    by_method: dict[str, int] = {}
    by_pstatus: dict[str, int] = {}

    for e in all_entries:
        if e.enabled:
            stats.enabled_sources += 1
        if e.parser_status == "parser_ready":
            stats.parser_ready_sources += 1
        if e.parser_status == "blocked":
            stats.blocked_sources += 1
        if e.source_level == "national":
            stats.national_sources += 1
        if e.province == "广东":
            stats.guangdong_sources += 1
        if e.source_level == "province" and e.province != "广东":
            stats.province_source_count += 1
        if e.city:
            stats.city_source_count += 1
        if e.source_type == "price":
            stats.price_source_count += 1
        if e.source_type == "attachment":
            stats.attachment_source_count += 1
        if e.acquisition_method == "manual_import":
            stats.manual_import_sources += 1
        if e.acquisition_method == "authorized_api":
            stats.authorized_api_sources += 1

        meth = e.acquisition_method or "unknown"
        by_method[meth] = by_method.get(meth, 0) + 1
        pst = e.parser_status or "unknown"
        by_pstatus[pst] = by_pstatus.get(pst, 0) + 1

    stats.by_acquisition_method = by_method
    stats.by_parser_status = by_pstatus
    return stats
