#!/usr/bin/env bash
set -euo pipefail

printf 'Python: '
python --version
printf 'Alembic: '
alembic --version
printf 'DATABASE_URL: %s\n' "${DATABASE_URL:-<not set, app default PostgreSQL will be used>}"
printf 'VLLM_BASE_URL: %s\n' "${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
printf 'VLLM_MODEL: %s\n' "${VLLM_MODEL:-aeon-local}"
python - <<'PY'
from app.core.config import get_settings
settings = get_settings()
print(f"Resolved database_url: {settings.database_url}")
print(f"Resolved vllm_base_url: {settings.vllm_base_url}")
print(f"Resolved vllm_model: {settings.vllm_model}")
PY
