#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///./local_dev.db}"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
export VLLM_MODEL="${VLLM_MODEL:-aeon-local}"

alembic upgrade head
python -m app.seed.seed_data
uvicorn app.main:app --reload --host "${HOST:-127.0.0.1}" --port "${PORT:-9000}"
