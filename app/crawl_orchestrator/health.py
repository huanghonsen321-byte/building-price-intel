"""Orchestrator health checks."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crawl_orchestrator import CrawlRun, CrawlRunSource


def get_health(db: Session) -> dict:
    runs = list(db.scalars(
        select(CrawlRun).order_by(CrawlRun.created_at.desc()).limit(10)
    ))
    return {
        "total_runs": len(runs),
        "latest_run": runs[0].id if runs else None,
        "latest_status": runs[0].status if runs else "no_runs",
    }


def get_latest_run(db: Session) -> CrawlRun | None:
    return db.scalar(
        select(CrawlRun).order_by(CrawlRun.created_at.desc())
    )


def get_failures(db: Session, limit: int = 30) -> list[CrawlRunSource]:
    return list(db.scalars(
        select(CrawlRunSource).where(
            CrawlRunSource.status.in_(["blocked", "failed"])
        ).order_by(CrawlRunSource.id.desc()).limit(limit)
    ))


def get_runs(db: Session, limit: int = 20) -> list[CrawlRun]:
    return list(db.scalars(
        select(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit)
    ))


def get_run_sources(db: Session, run_id: int) -> list[CrawlRunSource]:
    return list(db.scalars(
        select(CrawlRunSource).where(CrawlRunSource.crawl_run_id == run_id)
    ))
