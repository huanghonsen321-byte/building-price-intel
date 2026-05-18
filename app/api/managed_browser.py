from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.managed_browser_run import ManagedBrowserRun

router = APIRouter(prefix="/api/managed-browser", tags=["managed-browser"])


@router.get("/runs")
def list_managed_browser_runs(
    source_name: str | None = None,
    keyword: str | None = None,
    blocked_reason: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(ManagedBrowserRun)
    if source_name:
        stmt = stmt.where(ManagedBrowserRun.source_name == source_name)
    if keyword:
        stmt = stmt.where(ManagedBrowserRun.keyword.ilike(f"%{keyword}%"))
    if blocked_reason:
        stmt = stmt.where(ManagedBrowserRun.blocked_reason == blocked_reason)

    from sqlalchemy import func
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            stmt.order_by(ManagedBrowserRun.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/runs/{run_id}")
def get_managed_browser_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ManagedBrowserRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run
