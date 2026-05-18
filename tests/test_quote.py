from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference


def test_quote_area_unit(client) -> None:
    client.post("/api/crawl/run", json={"keyword": "脚手架"})
    response = client.post("/api/quote/scaffold/calculate", json={"scaffold_type": "盘扣", "area_m2": 1000})
    assert response.status_code == 200
    data = response.json()
    assert data["reference_count"] >= 1
    if data["calculated_unit"] == "元/㎡":
        assert data["estimated_amount"] is not None


def test_quote_missing_required_fields_returns_null_estimate(client) -> None:
    client.post("/api/crawl/run", json={"keyword": "脚手架"})
    response = client.post("/api/quote/scaffold/calculate", json={"scaffold_type": "盘扣"})
    assert response.status_code == 200
    data = response.json()
    if data["calculated_unit"] == "元/㎡":
        assert data["estimated_amount"] is None
        assert "area_m2" in data["formula"]


def test_quote_ton_day_unit(client) -> None:
    suffix = uuid4().hex
    scaffold_type = f"吨日脚手架-{suffix}"
    with SessionLocal() as db:
        case = ScaffoldBidCase(
            project_name=f"吨日计费项目-{suffix}",
            province="测试省",
            city="测试市",
            scaffold_type=scaffold_type,
            procurement_type="租赁",
            source_url=f"https://example.test/bids/{suffix}",
            publish_date=date.today(),
            extraction_confidence=Decimal("0.9"),
            review_status="pending",
        )
        db.add(case)
        db.flush()
        db.add(
            ScaffoldPriceReference(
                bid_case_id=case.id,
                price_type="manual_test",
                scaffold_type=scaffold_type,
                region="测试市",
                calculated_unit="元/吨/天",
                calculated_price=Decimal("8.50"),
                formula="manual test",
                confidence="high",
            )
        )
        db.commit()

    response = client.post(
        "/api/quote/scaffold/calculate",
        json={"scaffold_type": scaffold_type, "region": "测试市", "tonnage": 10, "rental_days": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["calculated_unit"] == "元/吨/天"
    assert data["estimated_amount"] == "2550.00"
    assert "tonnage" not in data["formula"]


def test_quote_uses_only_matching_unit_references(client) -> None:
    suffix = uuid4().hex
    scaffold_type = f"混合单位脚手架-{suffix}"
    with SessionLocal() as db:
        case = ScaffoldBidCase(
            project_name=f"混合单位项目-{suffix}",
            province="测试省",
            city="测试市",
            scaffold_type=scaffold_type,
            procurement_type="租赁",
            source_url=f"https://example.test/mixed-unit-bids/{suffix}",
            publish_date=date.today(),
            extraction_confidence=Decimal("0.9"),
            review_status="pending",
        )
        db.add(case)
        db.flush()
        db.add_all(
            [
                ScaffoldPriceReference(
                    bid_case_id=case.id,
                    price_type="manual_area_test",
                    scaffold_type=scaffold_type,
                    region="测试市",
                    calculated_unit="元/㎡",
                    calculated_price=Decimal("20.00"),
                    formula="manual area test",
                    confidence="high",
                ),
                ScaffoldPriceReference(
                    bid_case_id=case.id,
                    price_type="manual_month_test",
                    scaffold_type=scaffold_type,
                    region="测试市",
                    calculated_unit="元/月",
                    calculated_price=Decimal("10000.00"),
                    formula="manual month test",
                    confidence="low",
                ),
            ]
        )
        db.commit()

    response = client.post(
        "/api/quote/scaffold/calculate",
        json={"scaffold_type": scaffold_type, "region": "测试市", "area_m2": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["calculated_unit"] == "元/㎡"
    assert data["reference_price"] == "20.00"
    assert data["estimated_amount"] == "2000.00"
    assert data["reference_count"] == 1
