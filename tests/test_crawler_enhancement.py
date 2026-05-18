from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.crawlers.crawlee_spiders.run_crawlee import parse_records
from app.crawlers.standard_output import StandardCrawlerRecord, write_standard_record
from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference
from app.models.crawl import CrawlSource
from app.models.price import PriceDaily


def test_standard_price_record_writes_price_daily_and_source() -> None:
    record = StandardCrawlerRecord(
        record_type="price",
        source_name="测试公开价格源",
        source_url="https://example.com/steel-prices",
        crawl_time=datetime.now(UTC),
        publish_time=datetime(2026, 5, 18, tzinfo=UTC),
        category="steel",
        region="华北",
        city="北京",
        product_name="螺纹钢",
        specification="HRB400E 20mm",
        unit="元/吨",
        price=Decimal("3560"),
    )
    with SessionLocal() as db:
        assert write_standard_record(db, record) is True
        assert write_standard_record(db, record) is False
        price = db.scalar(select(PriceDaily).where(PriceDaily.source_name == "测试公开价格源"))
        assert price is not None
        assert price.price == Decimal("3560.00")
        source = db.scalar(select(CrawlSource).where(CrawlSource.name == "测试公开价格源"))
        assert source is not None
        assert source.source_type == "standard_price"


def test_standard_bid_and_reference_records_write_backend_tables() -> None:
    bid = StandardCrawlerRecord(
        record_type="bid",
        source_name="测试公开公告源",
        source_url="https://example.com/bid/1",
        crawl_time=datetime.now(UTC),
        publish_time=datetime(2026, 5, 18, tzinfo=UTC),
        region="广东",
        city="深圳",
        product_name="盘扣",
        type="中标公告",
        title="深圳医院项目盘扣式脚手架租赁服务中标公告",
        text_content="采购人：深圳市建设发展有限公司。中标人：深圳市安建周转材料有限公司。中标金额：3200000元。",
        amount=Decimal("3200000"),
        extra={"winner": "深圳市安建周转材料有限公司", "area_m2": Decimal("50000"), "rental_days": 200},
    )
    reference = StandardCrawlerRecord(
        record_type="reference",
        source_name="测试公开公告源",
        source_url="https://example.com/bid/1",
        crawl_time=datetime.now(UTC),
        region="深圳",
        product_name="盘扣",
        type="amount_per_area",
        unit="元/㎡",
        price=Decimal("64.00"),
        extra={"formula": "3200000 / 50000", "confidence": "medium"},
    )
    with SessionLocal() as db:
        assert write_standard_record(db, bid) is True
        write_standard_record(db, reference)
        case = db.scalar(select(ScaffoldBidCase).where(ScaffoldBidCase.source_url == "https://example.com/bid/1"))
        assert case is not None
        assert case.bid_amount == Decimal("3200000.00")
        ref = db.scalar(select(ScaffoldPriceReference).where(ScaffoldPriceReference.bid_case_id == case.id))
        assert ref is not None
        assert ref.calculated_price == Decimal("64.00")


def test_crawlee_adapter_parses_standard_records() -> None:
    html = """
    <html><head><title>深圳医院项目盘扣式脚手架租赁服务中标公告</title></head><body>
    <table><tr><td>2026-05-18</td><td>螺纹钢</td><td>HRB400E 20mm</td><td>北京</td><td>3560</td><td>元/吨</td></tr></table>
    <p>深圳医院项目盘扣式脚手架租赁服务中标公告。中标金额：3200000元。</p>
    </body></html>
    """
    records = parse_records(html, "https://example.com/page", "测试Crawlee")
    assert any(item.record_type == "price" and item.product_name == "螺纹钢" for item in records)
    assert any(item.record_type == "bid" and item.amount == Decimal("3200000") for item in records)
