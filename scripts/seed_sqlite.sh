#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///./local_dev.db}"
alembic upgrade head
python -m app.seed.seed_data
