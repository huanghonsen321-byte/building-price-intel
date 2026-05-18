import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_crawl_and_quote_flow() -> None:
    client = TestClient(app)
    crawl = client.post("/api/crawl/run", json={"keyword": "脚手架"})
    assert crawl.status_code == 200
    assert crawl.json()["task"]["status"] == "success"

    bids = client.get("/api/scaffold/bids")
    assert bids.status_code == 200
    assert len(bids.json()) >= 1

    refs = client.get("/api/scaffold/prices/reference")
    assert refs.status_code == 200
    assert len(refs.json()) >= 1

    quote = client.post("/api/quote/scaffold/calculate", json={"scaffold_type": "盘扣", "area_m2": 1000})
    assert quote.status_code == 200
    assert quote.json()["reference_count"] >= 1
