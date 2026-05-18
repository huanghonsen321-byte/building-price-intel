"""Runner — execute crawl plans and produce reports."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.crawl_orchestrator.planner import plan
from app.crawl_orchestrator.schemas import (
    PlanConfig,
    RunReport,
    SourcePlan,
    SourceResult,
)
from app.models.crawl_orchestrator import CrawlRun, CrawlRunSource

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "crawlers" / "output"


def _save_crawl_run(
    db: Session,
    config: PlanConfig,
    sources: list[SourcePlan],
    keywords: list[str],
) -> CrawlRun:
    run = CrawlRun(
        run_type=config.plan,
        status="running",
        started_at=datetime.now(UTC),
        keywords=keywords,
        source_filters={
            "plan": config.plan,
            "max_sources": config.max_sources,
            "max_keywords": config.max_keywords,
        },
        total_sources=len(sources),
        total_keywords=len(keywords),
    )
    db.add(run)
    db.flush()

    for sp in sources:
        db.add(CrawlRunSource(
            crawl_run_id=run.id,
            source_name=sp.source_name,
            source_url=sp.source_url,
            province=sp.province,
            city=sp.city,
            parser_name=sp.parser_name,
            parser_status=sp.parser_status,
            status="pending",
        ))
    db.flush()
    return run


def _run_single_source(
    db: Session,
    source: SourcePlan,
    keyword: str,
    use_vllm: bool,
    source_entry,
) -> SourceResult:
    """Run one source+keyword crawl. Returns SourceResult."""
    from app.services.crawl_service import run_public_crawl

    started = time.monotonic()
    result = SourceResult(source_name=source.source_name)

    try:
        task = run_public_crawl(db, keyword=keyword)
        elapsed = int((time.monotonic() - started) * 1000)

        if task.status == "success":
            if task.total_found > 0:
                result.status = "success"
            else:
                result.status = "no_match"
        elif task.error_message and any(
            kw in (task.error_message or "") for kw in ("blocked_403", "captcha", "login", "paid")
        ):
            result.status = "blocked"
            result.blocked_reason = task.error_message[:64]
        else:
            result.status = "failed"
            result.error_message = task.error_message

        result.total_found = task.total_found or 0
        result.total_saved = task.total_saved or 0
        result.duration_ms = elapsed
    except Exception as exc:
        result.status = "failed"
        result.error_message = str(exc)[:1000]
        result.duration_ms = int((time.monotonic() - started) * 1000)

    return result


def _update_crawl_run_source(
    db: Session, run_id: int, source_name: str, result: SourceResult,
) -> None:
    entry = db.scalar(
        select(CrawlRunSource).where(
            CrawlRunSource.crawl_run_id == run_id,
            CrawlRunSource.source_name == source_name,
        )
    )
    if entry:
        entry.status = result.status
        entry.blocked_reason = result.blocked_reason
        entry.total_found = result.total_found
        entry.total_saved = result.total_saved
        entry.error_message = result.error_message
        entry.duration_ms = result.duration_ms
        entry.started_at = datetime.now(UTC)
        entry.finished_at = datetime.now(UTC)
        db.flush()


def _send_notification(report: RunReport, no_wecom: bool) -> str:
    """Send WeCom summary or mock. Returns notification status."""
    if no_wecom:
        return "skipped"

    try:
        from app.services.notification_service import send_daily_briefing
        with SessionLocal() as db:
            briefing = send_daily_briefing(db, channel="mock")
            return briefing.status if briefing else "mock_sent"
    except Exception:
        return "send_failed"


def dry_run(config: PlanConfig) -> RunReport:
    """Dry-run: plan but don't execute any network or DB operations."""
    sources, keywords = plan(config)

    report = RunReport(
        plan=config.plan,
        status="dry-run",
        keywords=keywords,
        sources_selected=len(sources),
    )
    report.source_results = [
        SourceResult(source_name=s.source_name, status="skipped")
        for s in sources
    ]
    return report


def run(config: PlanConfig) -> RunReport:
    """Execute a crawl run end-to-end."""
    sources, keywords = plan(config)
    started = datetime.now(UTC)

    with SessionLocal() as db:
        crawl_run = _save_crawl_run(db, config, sources, keywords)
        run_id = crawl_run.id

        report = RunReport(
            run_id=run_id,
            plan=config.plan,
            status="running",
            started_at=started.isoformat(),
            keywords=keywords,
            sources_selected=len(sources),
        )

        all_sources = sources.copy()
        source_results: list[SourceResult] = []

        for source in all_sources:
            sr = SourceResult(source_name=source.source_name, status="pending")
            for keyword in keywords:
                if source.parser_name:
                    result = _run_single_source(db, source, keyword, config.use_vllm, source)
                    sr = result
                    if result.status in ("blocked", "failed"):
                        break  # Stop this source on block/fail
                else:
                    sr.status = "skipped"
            source_results.append(sr)
            _update_crawl_run_source(db, run_id, source.source_name, sr)

            if config.sleep_seconds > 0:
                time.sleep(config.sleep_seconds)

        # Aggregate
        report.source_results = source_results
        report.sources_success = sum(1 for r in source_results if r.status == "success")
        report.sources_no_match = sum(1 for r in source_results if r.status == "no_match")
        report.sources_blocked = sum(1 for r in source_results if r.status == "blocked")
        report.sources_failed = sum(1 for r in source_results if r.status == "failed")
        report.total_found = sum(r.total_found for r in source_results)
        report.total_saved = sum(r.total_saved for r in source_results)

        # Send notification
        notif_status = _send_notification(report, config.no_wecom)
        report.notification_status = notif_status

        # Write report
        report_path = write_report(report)
        report.report_path = report_path

        # Update crawl_run
        finished = datetime.now(UTC)
        crawl_run.status = (
            "success" if report.sources_blocked == 0 and report.sources_failed == 0
            else "partial_success" if report.sources_success > 0
            else "failed"
        )
        crawl_run.finished_at = finished
        crawl_run.total_found = report.total_found
        crawl_run.total_saved = report.total_saved
        crawl_run.notification_status = notif_status
        crawl_run.report_path = report_path
        if report.errors:
            crawl_run.error_message = "; ".join(report.errors)[:2000]
        db.commit()

        report.finished_at = finished.isoformat()
        report.duration_seconds = (finished - started).total_seconds()
        report.status = crawl_run.status

    return report


def write_report(report: RunReport) -> str:
    """Write run report JSON to output directory. Returns file path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"auto_crawl_run_{ts}.json"
    data = {
        "run_id": report.run_id,
        "plan": report.plan,
        "status": report.status,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "duration_seconds": report.duration_seconds,
        "keywords": report.keywords,
        "sources_selected": report.sources_selected,
        "sources_success": report.sources_success,
        "sources_no_match": report.sources_no_match,
        "sources_blocked": report.sources_blocked,
        "sources_failed": report.sources_failed,
        "total_found": report.total_found,
        "total_saved": report.total_saved,
        "total_duplicates": report.total_duplicates,
        "attachments_found": report.attachments_found,
        "attachments_parsed": report.attachments_parsed,
        "ai_extracted": report.ai_extracted,
        "review_tasks_created": report.review_tasks_created,
        "notification_channel": report.notification_channel,
        "notification_status": report.notification_status,
        "errors": report.errors,
        "source_results": [
            {"name": r.source_name, "status": r.status, "blocked_reason": r.blocked_reason,
             "found": r.total_found, "saved": r.total_saved}
            for r in report.source_results
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
