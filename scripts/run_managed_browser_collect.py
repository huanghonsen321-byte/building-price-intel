#!/usr/bin/env python3
"""Managed browser collection runner.

Compliance-first: only visits allowlisted domains.
Never saves cookies/tokens, never bypasses captcha/login/403/paywall.

Usage:
  python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --dry-run
  python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --manual-login
  python scripts/run_managed_browser_collect.py --source gzggzy --keyword 盘扣 --download-attachments
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.crawlers.managed_browser import (
    BrowserCollectorConfig,
    BrowserRunResult,
    dry_run_collect,
    live_collect,
    manual_login_collect,
    _save_run_record,
    load_allowlist,
)


def _print_result(result: BrowserRunResult, as_json: bool = False) -> None:
    data = {
        "source_name": result.source_name,
        "keyword": result.keyword,
        "mode": result.mode,
        "visited_urls_count": len(result.visited_urls),
        "downloaded_files_count": len(result.downloaded_files),
        "records_created": result.records_created,
        "attachments_created": result.attachments_created,
        "blocked_reason": result.blocked_reason,
        "error_message": result.error_message,
        "visited_urls": result.visited_urls[:10],
    }
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== Managed Browser Run ===")
        print(f"Source:  {result.source_name}")
        print(f"Keyword: {result.keyword}")
        print(f"Mode:    {result.mode}")
        print(f"Visited: {len(result.visited_urls)} URLs")
        print(f"Records: {result.records_created}")
        print(f"Attachments: {result.attachments_created}")
        if result.blocked_reason:
            print(f"BLOCKED: {result.blocked_reason}")
        if result.error_message:
            print(f"ERROR:   {result.error_message}")
        if result.visited_urls:
            print(f"\nVisited URLs:")
            for u in result.visited_urls[:10]:
                print(f"  {u}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Managed browser collection for authorized public pages"
    )
    parser.add_argument(
        "--source", required=True,
        help="Source key (ggzy, ccgp, zycg, ygp, gdgpo, gzggzy)"
    )
    parser.add_argument(
        "--keyword", required=True,
        help="Search keyword (e.g. 脚手架, 盘扣, 钢管)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate config only, no network, no DB writes"
    )
    parser.add_argument(
        "--manual-login", action="store_true",
        help="Open browser for manual login before collection"
    )
    parser.add_argument(
        "--download-attachments", action="store_true",
        help="Download and parse PDF/DOCX/XLSX attachments"
    )
    parser.add_argument(
        "--headless", action="store_true", default=True,
        help="Run browser in headless mode (default)"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Show browser window"
    )
    parser.add_argument(
        "--max-results", type=int, default=20,
        help="Max announcement pages to visit (default: 20)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of human-readable"
    )

    args = parser.parse_args()

    # Validate source key
    allowlist_data = load_allowlist()
    if args.source not in allowlist_data.get("source_mappings", {}):
        print(f"Unknown source key: {args.source}", file=sys.stderr)
        print(f"Available: {list(allowlist_data.get('source_mappings', {}).keys())}", file=sys.stderr)
        return 2

    # Determine mode
    if args.dry_run:
        mode = "dry-run"
    elif args.manual_login:
        mode = "manual-login"
    else:
        mode = "run"

    config = BrowserCollectorConfig(
        source_key=args.source,
        keyword=args.keyword,
        mode=mode,
        download_attachments=args.download_attachments,
        headless=not args.no_headless,
        max_results=args.max_results,
    )

    if mode == "dry-run":
        result = dry_run_collect(config)
        _print_result(result, as_json=args.json)
        return 0 if not result.error_message else 1

    # Live modes require DB
    with SessionLocal() as db:
        if mode == "manual-login":
            result = manual_login_collect(config, db)
        else:
            result = live_collect(config, db)
        db.commit()
        _print_result(result, as_json=args.json)
        return 0 if not result.error_message else 1


if __name__ == "__main__":
    raise SystemExit(main())
