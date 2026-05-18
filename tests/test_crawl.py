from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.crawl import BidRawDocument
from app.services import crawl_service


def test_failed_crawl_rolls_back_partial_documents(client, monkeypatch) -> None:
    def fail_create_case(*args, **kwargs):
        raise RuntimeError("forced extraction failure")

    monkeypatch.setattr(
        crawl_service, "create_or_update_case_from_extraction", fail_create_case
    )

    with SessionLocal() as db:
        before_count = len(
            db.scalars(
                select(BidRawDocument).where(
                    BidRawDocument.source_url.like(
                        "https://mock-public-bid.local/notice/%"
                    )
                )
            ).all()
        )

    response = client.post("/api/crawl/run", json={"keyword": "脚手架"})

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["status"] == "failed"
    assert "forced extraction failure" in task["error_message"]

    with SessionLocal() as db:
        after_count = len(
            db.scalars(
                select(BidRawDocument).where(
                    BidRawDocument.source_url.like(
                        "https://mock-public-bid.local/notice/%"
                    )
                )
            ).all()
        )
    assert after_count == before_count
