#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:9000}"

curl -fsS "${BASE_URL}/api/health"
echo
curl -fsS "${BASE_URL}/api/prices?page=1&page_size=5"
echo
curl -fsS "${BASE_URL}/api/scaffold/bids?page=1&page_size=5"
echo
curl -fsS "${BASE_URL}/api/scaffold/prices/reference?page=1&page_size=5"
echo
curl -fsS -X POST "${BASE_URL}/api/quote/scaffold/calculate" \
  -H 'Content-Type: application/json' \
  -d '{"scaffold_type":"盘扣","region":"呼和浩特","area_m2":1000,"rental_days":90}'
echo
