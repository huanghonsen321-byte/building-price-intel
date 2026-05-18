def _ensure_crawl_data(client) -> None:
    crawl = client.post("/api/crawl/run", json={"keyword": "脚手架"})
    assert crawl.status_code == 200
    assert crawl.json()["task"]["status"] == "success"


def test_scaffold_bids_list_uses_page_contract(client) -> None:
    _ensure_crawl_data(client)
    response = client.get("/api/scaffold/bids?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "page", "page_size"}
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_scaffold_bids_support_filters(client) -> None:
    _ensure_crawl_data(client)
    response = client.get(
        "/api/scaffold/bids",
        params={
            "keyword": "脚手架",
            "province": "内蒙古",
            "scaffold_type": "盘扣",
            "review_status": "pending",
            "page": 1,
            "page_size": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    for item in data["items"]:
        assert item["province"] == "内蒙古"
        assert item["scaffold_type"] == "盘扣"
        assert item["review_status"] == "pending"


def test_scaffold_price_references_list_uses_page_contract(client) -> None:
    _ensure_crawl_data(client)
    response = client.get("/api/scaffold/prices/reference?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "page", "page_size"}
    assert data["total"] >= 1
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_scaffold_bid_review_rejects_invalid_status(client) -> None:
    _ensure_crawl_data(client)
    list_response = client.get("/api/scaffold/bids?page=1&page_size=1")
    assert list_response.status_code == 200
    case_id = list_response.json()["items"][0]["id"]

    response = client.post(f"/api/scaffold/bids/{case_id}/review", json={"status": "done"})
    assert response.status_code == 422


def test_crawl_failure_records_failed_task_and_session_recovers(client, monkeypatch) -> None:
    def raise_search(self, keyword):
        raise RuntimeError("crawler unavailable")

    monkeypatch.setattr("app.services.crawl_service.MockPublicBidCrawler.search", raise_search)
    response = client.post("/api/crawl/run", json={"keyword": "脚手架"})
    assert response.status_code == 200
    task = response.json()["task"]
    assert task["status"] == "failed"
    assert "crawler unavailable" in task["error_message"]

    tasks_response = client.get("/api/crawl/tasks")
    assert tasks_response.status_code == 200
    assert tasks_response.json()[0]["id"] == task["id"]
