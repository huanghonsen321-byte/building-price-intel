from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.database import Base, SessionLocal, engine
from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference
from app.models.crawl import BidRawDocument
from app.models.price import PriceDaily
from app.models.review import ReviewTask
from app.services.price_reference_service import replace_reference_for_case


MOCK_SOURCE = "mock-seed"


def reset_mock_data() -> None:
    with SessionLocal() as db:
        mock_cases = select(ScaffoldBidCase.id).where(ScaffoldBidCase.source_url.like("https://mock-seed.local/%"))
        db.execute(delete(ReviewTask).where(ReviewTask.case_id.in_(mock_cases)))
        db.execute(delete(ScaffoldPriceReference).where(ScaffoldPriceReference.bid_case_id.in_(mock_cases)))
        db.execute(delete(ScaffoldBidCase).where(ScaffoldBidCase.source_url.like("https://mock-seed.local/%")))
        db.execute(delete(BidRawDocument).where(BidRawDocument.source_name == MOCK_SOURCE))
        db.execute(delete(PriceDaily).where(PriceDaily.source_name == MOCK_SOURCE))
        db.commit()


def seed_prices() -> None:
    today = date.today()
    rows = []
    for offset in range(7):
        day = today - timedelta(days=offset)
        rows.extend(
            [
                PriceDaily(
                    date=day,
                    category="steel",
                    region="华北",
                    city="北京",
                    product_name="螺纹钢",
                    spec="HRB400E 20mm",
                    material="HRB400E",
                    unit="元/吨",
                    price=Decimal("3560") - offset * 8,
                    change_value=Decimal("8"),
                    tax_included=True,
                    source_name=MOCK_SOURCE,
                    source_url="https://mock-seed.local/prices/steel",
                ),
                PriceDaily(
                    date=day,
                    category="scrap",
                    region="华北",
                    city="天津",
                    product_name="重废",
                    spec="6mm以上",
                    material="废钢",
                    unit="元/吨",
                    price=Decimal("2430") - offset * 5,
                    change_value=Decimal("5"),
                    tax_included=True,
                    source_name=MOCK_SOURCE,
                    source_url="https://mock-seed.local/prices/scrap",
                ),
                PriceDaily(
                    date=day,
                    category="scaffold",
                    region="内蒙古",
                    city="呼和浩特",
                    product_name="盘扣式脚手架租赁",
                    spec="48系",
                    material="Q355",
                    unit="元/吨/天",
                    price=Decimal("7.20") - Decimal(offset) * Decimal("0.03"),
                    change_value=Decimal("0.03"),
                    tax_included=True,
                    source_name=MOCK_SOURCE,
                    source_url="https://mock-seed.local/prices/scaffold",
                ),
            ]
        )
    with SessionLocal() as db:
        db.add_all(rows)
        db.commit()


def seed_bid_cases() -> None:
    with SessionLocal() as db:
        raw = BidRawDocument(
            source_name=MOCK_SOURCE,
            source_url="https://mock-seed.local/bids/001",
            title="呼和浩特商业综合体盘扣式脚手架租赁中标公告",
            publish_date=date.today() - timedelta(days=3),
            region="内蒙古",
            html_content="<p>盘扣式脚手架租赁中标公告</p>",
            text_content="中标金额2500000元，面积40000平方米，租期180天。",
            content_hash="seed-bid-001",
            crawl_status="saved",
        )
        db.add(raw)
        db.flush()
        case = ScaffoldBidCase(
            raw_document_id=raw.id,
            project_name="呼和浩特商业综合体盘扣式脚手架租赁",
            province="内蒙古",
            city="呼和浩特",
            district="赛罕区",
            buyer="内蒙古建设投资有限公司",
            agency="内蒙古招标代理有限公司",
            winner="呼和浩特市安建周转材料有限公司",
            bid_amount=Decimal("2500000"),
            announcement_type="中标公告",
            scaffold_type="盘扣",
            procurement_type="租赁",
            service_scope="盘扣式脚手架租赁、搭拆、运输及维护",
            duration_text="180天",
            quantity_text="40000平方米",
            area_m2=Decimal("40000"),
            rental_days=180,
            pricing_method="总价折算",
            source_url="https://mock-seed.local/bids/001",
            publish_date=date.today() - timedelta(days=3),
            ai_summary="商业综合体盘扣式脚手架租赁中标案例。",
            extraction_confidence=Decimal("0.65"),
            review_status="pending",
        )
        db.add(case)
        db.flush()
        replace_reference_for_case(db, case)
        db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    reset_mock_data()
    seed_prices()
    seed_bid_cases()
    print("seed data loaded")


if __name__ == "__main__":
    main()
