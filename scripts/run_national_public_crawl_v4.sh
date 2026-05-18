#!/usr/bin/env bash
# Hermes V4 safe national scaffold crawler runner.
# Bounded, compliant wrapper around the existing daily pipeline.
# It intentionally avoids "unlimited" concurrency, proxy rotation, login bypass,
# direct DB writes, and on-the-fly dependency installation.

set -euo pipefail

REPO_DIR="${BUILDING_PRICE_INTEL_DIR:-/home/huanghonsen/building-price-intel}"
CONFIG_FILE="${NATIONAL_CRAWL_CONFIG:-$REPO_DIR/app/crawlers/config/sources_national_v4.json}"
PYTHON_BIN="${BUILDING_PRICE_INTEL_PYTHON:-$REPO_DIR/.venv/bin/python}"
MODE="dry-run"
MAX_KEYWORDS=""
MAX_SOURCES=""
PROVINCE_FILTER=""
SOURCE_GROUP=""
NO_VLLM="--no-vllm"
NO_WECOM="0"

usage() {
  cat <<'USAGE'
Usage: scripts/run_national_public_crawl_v4.sh [--run] [--dry-run] [--province NAME] [--source-group NAME] [--max-keywords N] [--max-sources N] [--no-wecom] [--use-vllm]

Default is --dry-run. The runner:
  - reads app/crawlers/config/sources_national_v4.json
  - selects a bounded keyword batch
  - exports DAILY_CRAWL_KEYWORDS and retry env vars
  - delegates ingestion/extraction/summary/WeCom push to scripts/run_daily_ops.sh

Safety rules:
  - no proxy rotation
  - no login/captcha/paywall bypass
  - no direct SQLite writes
  - no pip install/playwright install inside production run
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) MODE="run"; shift ;;
    --dry-run) MODE="dry-run"; shift ;;
    --max-keywords) MAX_KEYWORDS="${2:?missing N}"; shift 2 ;;
    --max-sources) MAX_SOURCES="${2:?missing N}"; shift 2 ;;
    --province) PROVINCE_FILTER="${2:?missing province}"; shift 2 ;;
    --source-group) SOURCE_GROUP="${2:?missing source group}"; shift 2 ;;
    --no-wecom) NO_WECOM="1"; shift ;;
    --use-vllm) NO_VLLM=""; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

cd "$REPO_DIR"
mkdir -p app/crawlers/logs app/crawlers/output

if [[ -f "$REPO_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_DIR/.env"
  set +a
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config not found: $CONFIG_FILE" >&2
  exit 2
fi

CONFIG_JSON=$("$PYTHON_BIN" - <<'PY' "$CONFIG_FILE" "${MAX_KEYWORDS:-}" "${MAX_SOURCES:-}" "$PROVINCE_FILTER" "$SOURCE_GROUP"
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
max_keywords_arg, max_sources_arg, province_filter, source_group = sys.argv[2:6]
config = json.loads(path.read_text())
limits = config.get("limits", {})
max_keywords = int(max_keywords_arg or limits.get("max_keywords_per_run", 8))
max_sources = int(max_sources_arg or limits.get("max_sources_per_run", 4))
keywords = [item for item in config.get("keywords", []) if item][:max_keywords]

def source_matches(source):
    if source.get("enabled") is not True:
        return False
    if source_group and source_group.lower() == "guangdong":
        if source.get("province") != "广东" and "广东" not in source.get("regions", []):
            return False
    if province_filter:
        regions = source.get("regions", [])
        if source.get("province") != province_filter and province_filter not in regions:
            return False
    return True

price_sources = [item for item in config.get("price_sources", []) if source_matches(item)]
bid_sources = [item for item in config.get("bid_sources", []) if source_matches(item)]
# Province/source-group runs are bid-first; national default keeps existing enabled price/bid sources.
enabled_sources = (bid_sources if province_filter or source_group else price_sources + bid_sources)[:max_sources]
enabled_bid_sources = [item for item in enabled_sources if item.get("source_type") == "bid" or item in bid_sources]
print(json.dumps({
    "keywords": keywords,
    "enabled_sources": enabled_sources,
    "enabled_bid_sources": enabled_bid_sources,
    "limits": limits,
    "filters": {"province": province_filter, "source_group": source_group, "max_sources": max_sources},
}, ensure_ascii=False))
PY
)

KEYWORDS=$("$PYTHON_BIN" - <<'PY' "$CONFIG_JSON"
import json, sys
payload=json.loads(sys.argv[1])
print(','.join(payload['keywords']))
PY
)

if [[ -z "$KEYWORDS" ]]; then
  echo "No keywords selected from $CONFIG_FILE" >&2
  exit 2
fi

export DAILY_CRAWL_KEYWORDS="$KEYWORDS"
export DAILY_CRAWL_RETRY_ATTEMPTS="${DAILY_CRAWL_RETRY_ATTEMPTS:-3}"
export DAILY_CRAWL_RETRY_BACKOFF_SECONDS="${DAILY_CRAWL_RETRY_BACKOFF_SECONDS:-2}"
export DAILY_CRAWL_REQUEST_DELAY_SECONDS="${DAILY_CRAWL_REQUEST_DELAY_SECONDS:-2}"
export DAILY_CRAWL_SOURCE_CONFIG_JSON=$("$PYTHON_BIN" - <<'PY' "$CONFIG_JSON"
import json, sys
payload=json.loads(sys.argv[1])
print(json.dumps(payload.get("enabled_bid_sources", []), ensure_ascii=False))
PY
)
export DAILY_BRIEFING_REGIONS="${DAILY_BRIEFING_REGIONS:-广东,华北,内蒙古,全国}"
export DAILY_BRIEFING_CATEGORIES="${DAILY_BRIEFING_CATEGORIES:-steel,scrap,scaffold}"
export BID_ALERT_KEYWORDS="${BID_ALERT_KEYWORDS:-脚手架,盘扣,租赁,钢管,周转材料}"
export BID_ALERT_REGIONS="${BID_ALERT_REGIONS:-广东,广州,深圳,佛山,内蒙古,华北,全国}"

REPORT_PATH="app/crawlers/output/national_v4_$(date +%Y%m%d_%H%M%S).json"

echo "Hermes V4 safe national crawler"
echo "Mode: $MODE"
echo "Config: $CONFIG_FILE"
echo "Keywords: $DAILY_CRAWL_KEYWORDS"
echo "Retry: attempts=$DAILY_CRAWL_RETRY_ATTEMPTS backoff=${DAILY_CRAWL_RETRY_BACKOFF_SECONDS}s delay=${DAILY_CRAWL_REQUEST_DELAY_SECONDS}s"
echo "Filters: province=${PROVINCE_FILTER:-all} source_group=${SOURCE_GROUP:-all} max_sources=${MAX_SOURCES:-config}"
echo "Enabled sources:"
"$PYTHON_BIN" - <<'PY' "$CONFIG_JSON"
import json, sys
payload=json.loads(sys.argv[1])
for source in payload['enabled_sources']:
    print(f"- {source['name']} ({source['url']})")
PY

if [[ "$MODE" == "dry-run" ]]; then
  "$PYTHON_BIN" - <<'PY' "$CONFIG_JSON" "$REPORT_PATH"
import json, sys
from datetime import datetime, timezone
payload=json.loads(sys.argv[1])
report_path=sys.argv[2]
report={
    "ok": True,
    "mode": "dry-run",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "keywords": payload["keywords"],
    "enabled_sources": payload["enabled_sources"],
    "enabled_bid_sources": payload.get("enabled_bid_sources", []),
    "limits": payload["limits"],
    "filters": payload.get("filters", {}),
    "message": "Dry-run only: no network crawl, no DB writes, no WeCom push.",
}
open(report_path, 'w').write(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
PY
  echo "Dry-run report written to $REPORT_PATH"
  exit 0
fi

if [[ "$NO_WECOM" == "1" ]]; then
  export WECOM_WEBHOOK_URL=""
fi

set +e
./scripts/run_daily_ops.sh $NO_VLLM --json | tee "$REPORT_PATH"
STATUS=${PIPESTATUS[0]}
set -e

echo "Run report written to $REPORT_PATH"
exit "$STATUS"
