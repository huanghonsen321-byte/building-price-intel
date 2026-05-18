from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.ai.extractor import extract_scaffold_bid_sync
from app.core.database import SessionLocal
from app.models.bid import ScaffoldBidCase
from app.models.crawl import BidRawDocument
from app.models.price import PriceDaily
from app.models.review import ReviewTask
from app.services.ai_extraction_service import extract_pending_bid_documents
from app.services.price_summary_service import generate_today_price_summary


SAMPLE_NOTICE = """
广东省广州市白云区机场三期扩建安置区项目盘扣式脚手架租赁中标公告。
采购人：广州建工集团有限公司，代理机构：广东省机电招标中心有限公司。
中标人：佛山市顺德区某某脚手架租赁有限公司，中标金额：人民币 386.5 万元。
工程面积约 52000 平方米，盘扣脚手架约 860 吨，租期 180 天，包工包料综合单价。
公告发布日期：2026-05-18。来源链接：https://example.com/bid/ai-001
"""


def test_rule_based_scaffold_extraction_returns_required_fields_when_vllm_offline():
    result = extract_scaffold_bid_sync(
        SAMPLE_NOTICE,
        source_url="https://example.com/bid/ai-001",
        use_vllm=False,
    )

    assert result["is_scaffold_related"] is True
    assert result["project_name"] == "广东省广州市白云区机场三期扩建安置区项目盘扣式脚手架租赁"
    assert result["province"] == "广东省"
    assert result["city"] == "广州市"
    assert result["district"] == "白云区"
    assert result["buyer"] == "广州建工集团有限公司"
    assert result["agency"] == "广东省机电招标中心有限公司"
    assert result["winner"] == "佛山市顺德区某某脚手架租赁有限公司"
    assert result["bid_amount"] == Decimal("3865000")
    assert result["area_m2"] == Decimal("52000")
    assert result["tonnage"] == Decimal("860")
    assert result["rental_days"] == 180
    assert result["source_url"] == "https://example.com/bid/ai-001"
    assert "raw_evidence_snippets" in result and result["raw_evidence_snippets"]
    assert "missing_fields" in result
    assert Decimal(str(result["extraction_confidence"])) >= Decimal("0.70")


def test_extract_pending_documents_creates_review_task_for_low_confidence():
    with SessionLocal() as db:
        raw = BidRawDocument(
            source_name="pytest",
            source_url="https://example.com/bid/low-confidence",
            title="脚手架公告",
            publish_date=date.today(),
            region="广东省",
            text_content="脚手架相关公告，信息不完整，仅提到采购人：测试公司。",
            content_hash="low-confidence-ai-extraction",
        )
        db.add(raw)
        db.commit()

        cases = extract_pending_bid_documents(db, limit=5, use_vllm=False, confidence_threshold=Decimal("0.70"))

        assert len(cases) == 1
        case = cases[0]
        assert case.source_url == "https://example.com/bid/low-confidence"
        assert case.review_status == "pending"
        assert case.missing_fields
        assert case.raw_evidence_snippets
        task_count = db.scalar(select(ReviewTask).where(ReviewTask.case_id == case.id))
        assert task_count is not None


def test_generate_today_price_summary_reports_average_change_and_anomaly():
    with SessionLocal() as db:
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        db.add_all(
            [
                PriceDaily(date=yesterday, category="steel", region="广东", city="广州", product_name="盘扣脚手架", spec="48", unit="元/吨", price=Decimal("5000"), change_value=Decimal("0"), source_name="pytest"),
                PriceDaily(date=today, category="steel", region="广东", city="广州", product_name="盘扣脚手架", spec="48", unit="元/吨", price=Decimal("5200"), change_value=Decimal("200"), source_name="pytest"),
                PriceDaily(date=today, category="steel", region="广东", city="佛山", product_name="钢管", spec="Q235", unit="元/吨", price=Decimal("4100"), change_value=Decimal("-20"), source_name="pytest"),
            ]
        )
        db.commit()

        summary = generate_today_price_summary(db, category="steel")

        assert summary["date"] == today.isoformat()
        assert summary["total_records"] >= 2
        assert "今日行情摘要" in summary["summary_text"]
        assert "广东" in summary["summary_text"]
        assert summary["regions"]["广东"]["average_price"] > 0
        assert summary["anomalies"]
