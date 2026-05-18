"""Source library API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.source_library.registry import (
    get_source,
    get_sources,
    get_source_count,
    get_stats,
    load_source_library,
)
from app.source_library.schemas import SourceQuery
from app.source_library.validator import validate_source

router = APIRouter(prefix="/api/source-library", tags=["source-library"])


@router.get("")
def list_sources(
    province: str | None = None,
    city: str | None = None,
    source_level: str | None = None,
    source_type: str | None = None,
    acquisition_method: str | None = None,
    parser_status: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = SourceQuery(
        province=province,
        city=city,
        source_level=source_level,
        source_type=source_type,
        acquisition_method=acquisition_method,
        parser_status=parser_status,
        enabled=enabled,
        keyword=keyword,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    items = get_sources(query)
    total = get_source_count(query)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/stats")
def source_library_stats():
    return get_stats()


@router.get("/{source_id}")
def get_source_entry(source_id: str):
    """Get a single source by name or 1-based index."""
    # Try name first, then index
    entry = get_source(source_id)
    if entry is None and source_id.isdigit():
        entry = get_source(int(source_id))
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="source not found")
    return entry


@router.post("/validate")
def validate_source_url(name: str):
    """Validate a source URL. Does NOT bypass 403/captcha/login/paywall."""
    entry = get_source(name)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="source not found")
    return validate_source(entry)


@router.post("/{source_id}/enable")
def enable_source(source_id: str):
    """Enable a source (runtime only, does not persist to JSON)."""
    entry = get_source(source_id)
    if entry is None and source_id.isdigit():
        entry = get_source(int(source_id))
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="source not found")
    entry.enabled = True
    return {"name": entry.name, "enabled": entry.enabled}


@router.post("/{source_id}/disable")
def disable_source(source_id: str):
    """Disable a source (runtime only, does not persist to JSON)."""
    entry = get_source(source_id)
    if entry is None and source_id.isdigit():
        entry = get_source(int(source_id))
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="source not found")
    entry.enabled = False
    return {"name": entry.name, "enabled": entry.enabled}


@router.post("/import")
def import_sources(payload: list[dict]):
    """Import sources from JSON array. Returns validation results."""
    from app.source_library.schemas import validate_source_entry
    results = []
    for item in payload:
        errors = validate_source_entry(item)
        results.append({
            "name": item.get("name", ""),
            "valid": len(errors) == 0,
            "errors": errors,
        })
    return {"imported": len(payload), "results": results}
