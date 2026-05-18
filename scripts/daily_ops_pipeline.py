#!/usr/bin/env python3
"""Daily data pipeline for building-price-intel.

Runs without the FastAPI server:
1. Alembic migrations are expected to be run by the wrapper before this script.
2. Crawl public data sources for configured keywords.
3. Run AI/rule fallback extraction for pending raw bid documents.
4. Generate a Chinese market summary.
5. Send a daily briefing to WeCom when WECOM_WEBHOOK_URL is configured, otherwise use mock sender.
6. Send important bid alerts for newly created high-value matching cases.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.bid import ScaffoldBidCase  # noqa: E402
from app.services.ai_extraction_service import extract_pending_bid_documents  # noqa: E402
from app.services.crawl_service import run_public_crawl  # noqa: E402
from app.services.notification_service import alert_for_bid_case, send_daily_briefing  # noqa: E402
from app.services.price_summary_service import generate_today_price_summary  # noqa: E402


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _decimal_env(name: str, default: str) -> Decimal:
    try:
        return Decimal(os.getenv(name, default))
    except Exception:
        return Decimal(default)


def _channel_and_target() -> tuple[str, str | None]:
    webhook = os.getenv("WECOM_WEBHOOK_URL", "").strip()
    if webhook:
        return "wecom_webhook", webhook
    return "mock", "mock://daily-ops"


def run_pipeline(use_vllm: bool = True, pending_limit: int = 50) -> dict:
    started_at = datetime.now(UTC)
    keywords = _csv_env("DAILY_CRAWL_KEYWORDS", "脚手架,盘扣脚手架,钢材,废钢")
    briefing_regions = _csv_env("DAILY_BRIEFING_REGIONS", "广东,华北,内蒙古")
    briefing_categories = _csv_env("DAILY_BRIEFING_CATEGORIES", "steel,scrap,scaffold")
    alert_keywords = _csv_env("BID_ALERT_KEYWORDS", "脚手架,盘扣,租赁,钢管")
    alert_regions = _csv_env("BID_ALERT_REGIONS", "广东,广州,深圳,佛山,内蒙古,华北")
    min_amount = _decimal_env("BID_ALERT_MIN_AMOUNT", "1000000")
    channel, target = _channel_and_target()

    report: dict = {
        "started_at": started_at.isoformat(),
        "database_url": os.getenv("DATABASE_URL", ""),
        "notification_channel": channel,
        "keywords": keywords,
        "crawl_tasks": [],
        "extracted_cases": 0,
        "alerts_sent": 0,
        "alert_skipped": 0,
        "summary": None,
        "briefing_status": None,
        "errors": [],
    }

    with SessionLocal() as db:
        for keyword in keywords:
            task = run_public_crawl(db, keyword=keyword)
            report["crawl_tasks"].append(
                {
                    "keyword": keyword,
                    "task_id": task.id,
                    "status": task.status,
                    "total_found": task.total_found,
                    "total_saved": task.total_saved,
                    "error_message": task.error_message,
                }
            )
            if task.status != "success":
                report["errors"].append(f"crawl {keyword} failed: {task.error_message}")

        try:
            extracted = extract_pending_bid_documents(db, limit=pending_limit, use_vllm=use_vllm)
            report["extracted_cases"] = len(extracted)
        except Exception as exc:
            report["errors"].append(f"AI extraction failed: {exc}")

        summary = generate_today_price_summary(db)
        report["summary"] = {
            "date": summary.get("date"),
            "total_records": summary.get("total_records"),
            "summary_text": summary.get("summary_text"),
            "anomaly_count": len(summary.get("anomalies") or []),
        }

        briefing = send_daily_briefing(
            db,
            channel=channel,
            target=target,
            regions=briefing_regions,
            categories=briefing_categories,
        )
        report["briefing_status"] = briefing.status
        if briefing.error_message:
            report["errors"].append(f"briefing send failed: {briefing.error_message}")

        new_cases = list(
            db.scalars(
                select(ScaffoldBidCase)
                .where(ScaffoldBidCase.created_at >= started_at)
                .order_by(ScaffoldBidCase.id.desc())
                .limit(50)
            )
        )
        for case in new_cases:
            result = alert_for_bid_case(
                db,
                case,
                channel=channel,
                target=target,
                keywords=alert_keywords,
                regions=alert_regions,
                min_amount=min_amount,
            )
            if result is None:
                report["alert_skipped"] += 1
            elif result.status == "success":
                report["alerts_sent"] += 1
            else:
                report["errors"].append(f"alert send failed for case {case.id}: {result.error_message}")

    report["finished_at"] = datetime.now(UTC).isoformat()
    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-vllm", action="store_true", help="force offline rule-based extraction fallback")
    parser.add_argument("--pending-limit", type=int, default=50)
    parser.add_argument("--json", action="store_true", help="print compact JSON only")
    args = parser.parse_args()

    report = run_pipeline(use_vllm=not args.no_vllm, pending_limit=args.pending_limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, default=str))
    else:
        print("日常数据抓取 + AI行情摘要 + 企业微信提醒流水线完成")
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
