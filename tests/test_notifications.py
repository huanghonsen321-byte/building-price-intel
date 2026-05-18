from datetime import date
from decimal import Decimal

from app.core.database import SessionLocal
from app.models.bid import ScaffoldBidCase
from app.models.notification import NotificationLog
from app.models.price import PriceDaily
from app.services.notification_service import alert_for_bid_case, send_daily_briefing


def test_send_daily_briefing_uses_mock_sender_and_logs(client):
    with SessionLocal() as db:
        db.add(PriceDaily(date=date.today(), category="steel", region="广东", city="广州", product_name="盘扣脚手架", spec="48", unit="元/吨", price=Decimal("5200"), change_value=Decimal("80"), source_name="pytest"))
        db.commit()
        result = send_daily_briefing(db, channel="mock", target="mock://pytest", regions=["广东"], categories=["steel"])
        assert result.status == "success"
        assert "每日行情早报" in result.message
        assert db.query(NotificationLog).filter(NotificationLog.event_type == "daily_briefing").count() >= 1


def test_alert_for_bid_case_matches_keyword_amount_region_and_logs():
    with SessionLocal() as db:
        case = ScaffoldBidCase(
            project_name="广州白云机场盘扣脚手架租赁项目",
            province="广东省",
            city="广州市",
            buyer="广州测试建设有限公司",
            winner="佛山测试脚手架有限公司",
            bid_amount=Decimal("3500000"),
            scaffold_type="盘扣",
            procurement_type="租赁",
            source_url="https://example.com/notify-case",
            publish_date=date.today(),
            extraction_confidence=Decimal("0.9"),
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        result = alert_for_bid_case(
            db,
            case,
            channel="mock",
            target="mock://pytest",
            keywords=["盘扣", "机场"],
            regions=["广东"],
            min_amount=Decimal("3000000"),
        )

        assert result is not None
        assert result.status == "success"
        assert "重要公告提醒" in result.message
        assert db.query(NotificationLog).filter(NotificationLog.event_type == "bid_alert").count() >= 1
