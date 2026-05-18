PYTHON ?= python
PIP ?= pip
HOST ?= 127.0.0.1
PORT ?= 9000
SQLITE_DATABASE_URL ?= sqlite+pysqlite:///./local_dev.db

.PHONY: install migrate seed dev test api-test clean

install:
	$(PIP) install -r requirements.txt

migrate:
	alembic upgrade head

seed:
	$(PYTHON) -m app.seed.seed_data

dev:
	DATABASE_URL=$(SQLITE_DATABASE_URL) ./scripts/run_sqlite_dev.sh

test:
	pytest -q

api-test:
	./scripts/test_api.sh

clean:
	rm -f local_dev.db local_test.db *.db
	rm -rf .pytest_cache __pycache__ app/**/__pycache__ tests/**/__pycache__
