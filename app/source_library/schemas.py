"""Source library schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field


VALID_SOURCE_LEVELS = {"national", "province", "city", "enterprise", "industry", "price", "manual", "authorized"}
VALID_SOURCE_TYPES = {"bid", "price", "attachment", "search", "mixed"}
VALID_ACQUISITION_METHODS = {
    "national_aggregate_search", "official_search_page", "public_api",
    "html_list_page", "browser_discovery", "attachment_parse",
    "search_api_discovery", "manual_import", "authorized_api",
}
VALID_PARSER_STATUSES = {
    "not_started", "fixture_ready", "parser_ready", "blocked", "needs_browser", "deprecated",
}


@dataclass
class SourceEntry:
    name: str
    url: str = ""
    domain: str = ""
    source_level: str = "national"
    source_type: str = "bid"
    acquisition_method: str = "html_list_page"
    keywords: list[str] = field(default_factory=list)
    parser_name: str | None = None
    enabled: bool = False
    parser_status: str = "not_started"
    requires_browser: bool = False
    requires_manual_review: bool = False
    rate_limit_seconds: int = 3
    reliability_score: float = 0.0
    province: str | None = None
    city: str | None = None
    district: str | None = None
    country: str = "CN"
    public_api_found: bool = False
    public_page_reachable: bool = False
    last_success_at: str | None = None
    last_failed_at: str | None = None
    last_blocked_reason: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    category: str = ""


@dataclass
class SourceQuery:
    province: str | None = None
    city: str | None = None
    source_level: str | None = None
    source_type: str | None = None
    acquisition_method: str | None = None
    parser_status: str | None = None
    enabled: bool | None = None
    keyword: str | None = None
    tag: str | None = None
    limit: int = 200
    offset: int = 0


@dataclass
class SourceLibraryStats:
    total_sources: int = 0
    enabled_sources: int = 0
    parser_ready_sources: int = 0
    blocked_sources: int = 0
    national_sources: int = 0
    guangdong_sources: int = 0
    province_source_count: int = 0
    city_source_count: int = 0
    price_source_count: int = 0
    attachment_source_count: int = 0
    manual_import_sources: int = 0
    authorized_api_sources: int = 0
    by_acquisition_method: dict[str, int] = field(default_factory=dict)
    by_parser_status: dict[str, int] = field(default_factory=dict)


def validate_source_entry(entry: dict | SourceEntry) -> list[str]:
    """Validate a source entry dict. Returns list of validation errors (empty = valid)."""
    errors: list[str] = []

    if isinstance(entry, SourceEntry):
        d = entry.__dict__
    else:
        d = entry

    name = d.get("name", "")
    if not name or not isinstance(name, str):
        errors.append("name is required and must be a string")

    url = d.get("url", "")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        errors.append(f"url must start with http:// or https://: {url}")

    level = d.get("source_level", "")
    if level and level not in VALID_SOURCE_LEVELS:
        errors.append(f"invalid source_level: {level}")

    stype = d.get("source_type", "")
    if stype and stype not in VALID_SOURCE_TYPES:
        errors.append(f"invalid source_type: {stype}")

    method = d.get("acquisition_method", "")
    if method and method not in VALID_ACQUISITION_METHODS:
        errors.append(f"invalid acquisition_method: {method}")

    pstatus = d.get("parser_status", "")
    if pstatus and pstatus not in VALID_PARSER_STATUSES:
        errors.append(f"invalid parser_status: {pstatus}")

    return errors
