#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${BUILDING_PRICE_INTEL_DIR:-/home/huanghonsen/building-price-intel}"
PYTHON_BIN="${BUILDING_PRICE_INTEL_PYTHON:-/home/huanghonsen/projects/construction-price-app/building-price-intel/.venv/bin/python}"
DB_PATH="${BUILDING_PRICE_INTEL_DB:-$REPO_DIR/local_prod.db}"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///$DB_PATH}"

cd "$REPO_DIR"
alembic upgrade head >/dev/null
"$PYTHON_BIN" - <<'PY'
from app.core.database import SessionLocal
from app.services.price_summary_service import generate_today_price_summary
with SessionLocal() as db:
    summary = generate_today_price_summary(db)
print(summary.get('summary_text') or '暂无行情摘要')
PY
