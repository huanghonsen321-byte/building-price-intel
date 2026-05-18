#!/usr/bin/env python3
"""Automatic crawl orchestrator CLI.

Usage:
  python scripts/run_auto_crawl_orchestrator.py --dry-run --plan daily
  python scripts/run_auto_crawl_orchestrator.py --run --plan daily --max-sources 5 --max-keywords 5 --no-wecom
  python scripts/run_auto_crawl_orchestrator.py --run --plan guangdong --max-sources 3 --max-keywords 3 --no-wecom
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawl_orchestrator.runner import dry_run, run
from app.crawl_orchestrator.schemas import PlanConfig


def _print_report(report, as_json: bool = False) -> None:
    if as_json:
        data = {
            "plan": report.plan,
            "status": report.status,
            "keywords": report.keywords,
            "sources_selected": report.sources_selected,
            "sources_success": report.sources_success,
            "sources_no_match": report.sources_no_match,
            "sources_blocked": report.sources_blocked,
            "sources_failed": report.sources_failed,
            "total_found": report.total_found,
            "total_saved": report.total_saved,
            "duration_seconds": report.duration_seconds,
            "notification_status": report.notification_status,
            "errors": report.errors,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== Crawl Orchestrator Run ===")
        print(f"Plan:     {report.plan}")
        print(f"Status:   {report.status}")
        print(f"Keywords: {report.keywords}")
        print(f"Sources:  {len(report.source_results)} selected")
        if report.status != "dry-run":
            print(f"  Success:  {report.sources_success}")
            print(f"  No match: {report.sources_no_match}")
            print(f"  Blocked:  {report.sources_blocked}")
            print(f"  Failed:   {report.sources_failed}")
            print(f"Found:    {report.total_found}")
            print(f"Saved:    {report.total_saved}")
            print(f"Duration: {report.duration_seconds:.1f}s")
        if report.errors:
            print(f"Errors:   {len(report.errors)}")
        if report.report_path:
            print(f"Report:   {report.report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatic crawl orchestrator")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--plan", default="daily", choices=["daily", "guangdong", "national", "retry_failed", "retry-failed"])
    parser.add_argument("--max-sources", type=int, default=10)
    parser.add_argument("--max-keywords", type=int, default=8)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--no-wecom", action="store_true")
    parser.add_argument("--use-vllm", action="store_true")
    parser.add_argument("--write-report", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    mode = "dry-run" if args.dry_run else "run" if args.run else "dry-run"

    config = PlanConfig(
        plan=args.plan,
        max_sources=args.max_sources,
        max_keywords=args.max_keywords,
        sleep_seconds=args.sleep_seconds,
        no_wecom=args.no_wecom,
        use_vllm=args.use_vllm,
    )

    if mode == "dry-run":
        report = dry_run(config)
        _print_report(report, as_json=args.json)
        return 0

    report = run(config)
    _print_report(report, as_json=args.json)
    return 0 if report.status in ("success", "partial_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
