#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${BUILDING_PRICE_INTEL_DIR:-/home/huanghonsen/building-price-intel}"
if [ -f "$REPO_DIR/.env" ]; then
  set -a
  . "$REPO_DIR/.env"
  set +a
fi
PYTHON_BIN="${BUILDING_PRICE_INTEL_PYTHON:-/home/huanghonsen/projects/construction-price-app/building-price-intel/.venv/bin/python}"
DB_PATH="${BUILDING_PRICE_INTEL_DB:-$REPO_DIR/local_prod.db}"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///$DB_PATH}"
export DAILY_CRAWL_KEYWORDS="${DAILY_CRAWL_KEYWORDS:-脚手架,盘扣脚手架,钢材,废钢}"
export DAILY_BRIEFING_REGIONS="${DAILY_BRIEFING_REGIONS:-广东,华北,内蒙古}"
export DAILY_BRIEFING_CATEGORIES="${DAILY_BRIEFING_CATEGORIES:-steel,scrap,scaffold}"
export BID_ALERT_KEYWORDS="${BID_ALERT_KEYWORDS:-脚手架,盘扣,租赁,钢管}"
export BID_ALERT_REGIONS="${BID_ALERT_REGIONS:-广东,广州,深圳,佛山,内蒙古,华北}"
export BID_ALERT_MIN_AMOUNT="${BID_ALERT_MIN_AMOUNT:-1000000}"

cd "$REPO_DIR"
mkdir -p "$(dirname "$DB_PATH")" app/crawlers/logs

alembic upgrade head
if [ "${BOOTSTRAP_SEED_IF_EMPTY:-1}" = "1" ]; then
  PRICE_COUNT=$("$PYTHON_BIN" - <<'PY'
from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.price import PriceDaily
with SessionLocal() as db:
    print(db.scalar(select(func.count()).select_from(PriceDaily)) or 0)
PY
)
  if [ "$PRICE_COUNT" = "0" ]; then
    "$PYTHON_BIN" -m app.seed.seed_data
  fi
fi
"$PYTHON_BIN" scripts/daily_ops_pipeline.py "$@"
