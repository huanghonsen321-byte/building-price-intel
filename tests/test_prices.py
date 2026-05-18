def test_prices_list_uses_page_contract(client) -> None:
    response = client.get("/api/prices?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "page", "page_size"}
    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_prices_support_filters(client) -> None:
    response = client.get(
        "/api/prices",
        params={
            "category": "steel",
            "region": "华北",
            "city": "北京",
            "product_name": "螺纹钢",
            "page": 1,
            "page_size": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    for item in data["items"]:
        assert item["category"] == "steel"
        assert item["region"] == "华北"
        assert item["city"] == "北京"
        assert "螺纹钢" in item["product_name"]
