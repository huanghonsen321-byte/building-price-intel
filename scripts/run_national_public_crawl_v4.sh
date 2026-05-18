#!/usr/bin/env bash
# Hermes V4 safe national scaffold crawler runner.
# Now supports --source-library mode reading from source_library_national.json.

set -euo pipefail

REPO_DIR="${BUILDING_PRICE_INTEL_DIR:-/home/huanghonsen/building-price-intel}"
CONFIG_FILE="${NATIONAL_CRAWL_CONFIG:-$REPO_DIR/app/crawlers/config/sources_national_v4.json}"
SOURCE_LIBRARY="${SOURCE_LIBRARY_PATH:-$REPO_DIR/app/crawlers/config/source_library_national.json}"
PYTHON_BIN="${BUILDING_PRICE_INTEL_PYTHON:-$REPO_DIR/.venv/bin/python}"
MODE="dry-run"
MAX_KEYWORDS=""
MAX_SOURCES=""
PROVINCE_FILTER=""
CITY_FILTER=""
SOURCE_LEVEL_FILTER=""
SOURCE_TYPE_FILTER=""
PARSER_STATUS_FILTER=""
SOURCE_GROUP=""
NO_VLLM="--no-vllm"
NO_WECOM="0"
USE_SOURCE_LIBRARY="0"

usage() {
  cat <<'USAGE'
Usage: scripts/run_national_public_crawl_v4.sh [--run] [--dry-run]
  [--source-library] [--province NAME] [--city NAME] [--source-level NAME]
  [--source-type NAME] [--parser-status NAME] [--source-group NAME]
  [--max-keywords N] [--max-sources N] [--no-wecom] [--use-vllm]

Default is --dry-run.
--source-library: use source_library_national.json instead of sources_national_v4.json
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) MODE="run"; shift ;;
    --dry-run) MODE="dry-run"; shift ;;
    --source-library) USE_SOURCE_LIBRARY="1"; shift ;;
    --max-keywords) MAX_KEYWORDS="${2:?missing N}"; shift 2 ;;
    --max-sources) MAX_SOURCES="${2:?missing N}"; shift 2 ;;
    --province) PROVINCE_FILTER="${2:?missing province}"; shift 2 ;;
    --city) CITY_FILTER="${2:?missing city}"; shift 2 ;;
    --source-level) SOURCE_LEVEL_FILTER="${2:?missing level}"; shift 2 ;;
    --source-type) SOURCE_TYPE_FILTER="${2:?missing type}"; shift 2 ;;
    --parser-status) PARSER_STATUS_FILTER="${2:?missing status}"; shift 2 ;;
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
  . "$REPO_DIR/.env"
  set +a
fi

# Select config: source library or V4 config
if [[ "$USE_SOURCE_LIBRARY" == "1" ]]; then
  if [[ ! -f "$SOURCE_LIBRARY" ]]; then
    echo "Source library not found: $SOURCE_LIBRARY" >&2
    exit 2
  fi
  CONFIG_JSON=$("$PYTHON_BIN" - "$SOURCE_LIBRARY" "${MAX_KEYWORDS:-}" "${MAX_SOURCES:-}" "$PROVINCE_FILTER" "$CITY_FILTER" "$SOURCE_LEVEL_FILTER" "$SOURCE_TYPE_FILTER" "$PARSER_STATUS_FILTER" "$SOURCE_GROUP" <<'PY'
import json, sys
path, max_kw, max_src, prov, city, slevel, stype, pstatus, sgroup = sys.argv[1:10]
data = json.loads(open(path).read())
max_keywords = int(max_kw or 8)
max_sources = int(max_src or 10)

# Flatten all sources
all_sources = []
for cat_key in ("national_sources","guangdong_provincial_sources","guangdong_city_sources","national_province_sources","price_sources","manual_import_sources"):
    for s in data.get(cat_key, []):
        s["_category"] = cat_key
        all_sources.append(s)

# Filter
def matches(s):
    if prov and s.get("province") != prov:
        # Also check city name
        if s.get("city") != prov:
            return False
    if city and s.get("city") != city:
        return False
    if slevel and s.get("source_level") != slevel:
        return False
    if stype and s.get("source_type") != stype:
        return False
    if pstatus and s.get("parser_status") != pstatus:
        return False
    if sgroup:
        if sgroup.lower() == "guangdong" and s.get("province") != "广东":
            return False
        if sgroup.lower() == "national" and s.get("source_level") != "national":
            return False
    if s.get("parser_status") == "blocked" or s.get("parser_status") == "deprecated":
        return False
    return True

filtered = [s for s in all_sources if matches(s)]

# Separate price and bid sources
price_sources = [s for s in filtered if s.get("source_type") == "price"][:max_sources]
bid_sources = [s for s in filtered if s.get("source_type") in ("bid","mixed") or s.get("_category") in ("national_sources","guangdong_provincial_sources","guangdong_city_sources")][:max_sources]
enabled_sources = (price_sources + bid_sources)[:max_sources]

# Keywords - load from keyword library if available
keywords = []
kw_path = "/home/huanghonsen/building-price-intel/app/crawlers/config/keyword_library.json"
try:
    kw_data = json.loads(open(kw_path).read())
    keywords = kw_data.get("scaffold_keywords", [])[:max_keywords]
except:
    keywords = ["脚手架","盘扣","盘扣式脚手架","扣件式脚手架","钢管脚手架","模板脚手架","脚手架搭拆","周转材料租赁"][:max_keywords]

# Build source configs for crawl_service
enabled_bid_sources = []
for s in bid_sources:
    parser_name = s.get("parser_name")
    name = s.get("name","")
    url = s.get("url","")
    if parser_name and s.get("parser_status") == "parser_ready":
        enabled_bid_sources.append({
            "name": name, "url": url,
            "source_type": "real_public_bid",
            "parser_name": parser_name,
            "enabled": True,
        })

print(json.dumps({
    "keywords": keywords,
    "enabled_sources": [{"name":s["name"],"url":s["url"]} for s in enabled_sources],
    "enabled_bid_sources": enabled_bid_sources,
    "filters": {"province":prov,"city":city,"source_level":slevel,"source_type":stype,"parser_status":pstatus,"source_group":sgroup,"max_sources":max_sources},
    "total_sources": len(all_sources),
    "matched_sources": len(filtered),
}, ensure_ascii=False))
PY
  )
else
  # Original V4 config mode
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Config not found: $CONFIG_FILE" >&2
    exit 2
  fi
  CONFIG_JSON=$("$PYTHON_BIN" - "$CONFIG_FILE" "${MAX_KEYWORDS:-}" "${MAX_SOURCES:-}" "$PROVINCE_FILTER" "$SOURCE_GROUP" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
max_keywords_arg, max_sources_arg, province_filter, source_group = sys.argv[2:6]
config = json.loads(path.read_text())
limits = config.get("limits", {})
max_keywords = int(max_keywords_arg or limits.get("max_keywords_per_run", 8))
max_sources = int(max_sources_arg or limits.get("max_sources_per_run", 6))
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
fi

KEYWORDS=$("$PYTHON_BIN" - "$CONFIG_JSON" <<'PY'
import json, sys
payload=json.loads(sys.argv[1])
print(','.join(payload['keywords']))
PY
)

if [[ -z "$KEYWORDS" ]]; then
  echo "No keywords selected" >&2
  exit 2
fi

export DAILY_CRAWL_KEYWORDS="$KEYWORDS"
export DAILY_CRAWL_RETRY_ATTEMPTS="${DAILY_CRAWL_RETRY_ATTEMPTS:-3}"
export DAILY_CRAWL_RETRY_BACKOFF_SECONDS="${DAILY_CRAWL_RETRY_BACKOFF_SECONDS:-2}"
export DAILY_CRAWL_REQUEST_DELAY_SECONDS="${DAILY_CRAWL_REQUEST_DELAY_SECONDS:-2}"
export DAILY_CRAWL_SOURCE_CONFIG_JSON=$("$PYTHON_BIN" - "$CONFIG_JSON" <<'PY'
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
if [[ "$USE_SOURCE_LIBRARY" == "1" ]]; then
  echo "Config: $SOURCE_LIBRARY"
else
  echo "Config: $CONFIG_FILE"
fi

# Source library mode: show stats
if [[ "$USE_SOURCE_LIBRARY" == "1" ]]; then
  "$PYTHON_BIN" - "$CONFIG_JSON" <<'PY'
import json, sys
payload=json.loads(sys.argv[1])
kw_count = len(payload.get("keywords", []))
print(f"Total sources in library: {payload.get('total_sources', 0)}")
print(f"Matched sources: {payload.get('matched_sources', 0)}")
print(f"Keywords: {kw_count}")
print(f"Filters: {json.dumps(payload.get('filters', {}), ensure_ascii=False)}")
print("Enabled sources:")
for s in payload.get("enabled_sources", []):
    print(f"  - {s['name']} ({s.get('url','')})")
if payload.get("enabled_bid_sources"):
    print("Enabled bid sources with parsers:")
    for s in payload["enabled_bid_sources"]:
        print(f"  - {s['name']} -> {s['parser_name']}")
PY
else
  echo "Keywords: $DAILY_CRAWL_KEYWORDS"
  echo "Retry: attempts=$DAILY_CRAWL_RETRY_ATTEMPTS backoff=${DAILY_CRAWL_RETRY_BACKOFF_SECONDS}s delay=${DAILY_CRAWL_REQUEST_DELAY_SECONDS}s"
  echo "Filters: province=${PROVINCE_FILTER:-all} source_group=${SOURCE_GROUP:-all} max_sources=${MAX_SOURCES:-config}"
  echo "Enabled sources:"
  "$PYTHON_BIN" - "$CONFIG_JSON" <<'PY'
import json, sys
payload=json.loads(sys.argv[1])
for source in payload['enabled_sources']:
    print(f"  - {source['name']} ({source['url']})")
PY
fi

if [[ "$MODE" == "dry-run" ]]; then
  "$PYTHON_BIN" - "$CONFIG_JSON" "$REPORT_PATH" <<'PY'
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
    "filters": payload.get("filters", {}),
    "total_sources": payload.get("total_sources", 0),
    "matched_sources": payload.get("matched_sources", 0),
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
