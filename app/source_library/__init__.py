"""Source library — data source registry and operations."""

from __future__ import annotations

from app.source_library.schemas import (
    SourceEntry,
    SourceLibraryStats,
    SourceQuery,
    validate_source_entry,
)
from app.source_library.registry import (
    load_source_library,
    get_sources,
    get_source,
    get_source_count,
    get_stats,
)

__all__ = [
    "SourceEntry",
    "SourceLibraryStats",
    "SourceQuery",
    "load_source_library",
    "get_sources",
    "get_source",
    "get_source_count",
    "get_stats",
    "validate_source_entry",
]
