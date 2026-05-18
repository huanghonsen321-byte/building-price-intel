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
