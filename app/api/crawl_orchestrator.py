"""Crawl orchestrator API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crawl_orchestrator import CrawlRun
from app.crawl_orchestrator.health import (
    get_failures,
    get_health,
    get_latest_run,
    get_run_sources,
    get_runs,
)

router = APIRouter(prefix="/api/crawl-orchestrator", tags=["crawl-orchestrator"])


@router.get("/health")
def orchestrator_health(db: Session = Depends(get_db)):
    return get_health(db)


@router.get("/runs")
def list_runs(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    from sqlalchemy import func, select
    stmt = select(CrawlRun)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    items = list(db.scalars(stmt.order_by(CrawlRun.id.desc()).offset(offset).limit(page_size)))
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/runs/{run_id}")
def get_run_detail(run_id: int, db: Session = Depends(get_db)):
    run = db.get(CrawlRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    sources = get_run_sources(db, run_id)
    return {"run": run, "sources": sources}


@router.get("/latest")
def latest_run(db: Session = Depends(get_db)):
    run = get_latest_run(db)
    if run is None:
        raise HTTPException(status_code=404, detail="no runs found")
    sources = get_run_sources(db, run.id)
    return {"run": run, "sources": sources}


@router.get("/failures")
def failures(limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db)):
    return get_failures(db, limit=limit)


@router.post("/run")
def trigger_run(
    plan: str = Query(default="daily"),
    max_sources: int = Query(default=5, ge=1, le=50),
    max_keywords: int = Query(default=5, ge=1, le=20),
    no_wecom: bool = Query(default=True),
    use_vllm: bool = Query(default=False),
):
    from app.crawl_orchestrator.runner import run as orchestrator_run
    from app.crawl_orchestrator.schemas import PlanConfig

    config = PlanConfig(
        plan=plan,
        max_sources=max_sources,
        max_keywords=max_keywords,
        no_wecom=no_wecom,
        use_vllm=use_vllm,
    )
    report = orchestrator_run(config)
    return report
