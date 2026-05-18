#!/usr/bin/env python3
"""Backfill missing pending review tasks for historical scaffold bid cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.services.bid_service import backfill_review_tasks_for_pending_cases  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        result = backfill_review_tasks_for_pending_cases(db)
        db.commit()

    payload = {"ok": True, **result}
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
