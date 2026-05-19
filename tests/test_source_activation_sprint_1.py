from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.crawl_orchestrator import runner
from app.crawl_orchestrator.health import get_failures, get_latest_run, get_run_sources
from app.crawl_orchestrator.schemas import PlanConfig, SourcePlan
from app.models.bid import ScaffoldBidCase
from app.models.crawl import BidRawDocument
from app.models.review import ReviewTask
from app.services.crawl_service import run_public_crawl


YGP_API_BODY_WITH_RESULT = {
    "errcode": 0,
    "errmsg": "ok",
    "data": {
        "pageNo": 1,
        "pageSize": 10,
        "pageTotal": 1,
        "total": "1",
        "pageData": [
            {
                "docId": "sprint1-doc-001-3C14",
                "noticeId": "sprint1-doc-001",
                "noticeSecondType": "A",
                "noticeSecondTypeDesc": "工程建设",
                "noticeThirdTypeDesc": "招标公告与资格预审公告",
                "projectTypeName": "市政",
                "siteName": "深圳市",
                "regionName": "深圳市",
                "noticeTitle": "深圳市学校钢管脚手架租赁服务中标公告",
                "projectCode": "E440300SPRINT1001",
                "publishDate": "20260518120000",
                "edition": "v3",
                "tradingProcess": "3C14",
                "datasetName": "招标公告、资格预审公告",
                "pubServicePlat": "深圳公共资源交易平台",
            }
        ],
    },
}


def test_successful_source_can_write_raw_docs_cases_and_review_tasks(monkeypatch) -> None:
    from app.crawlers.real_public_sources import GuangdongPublicResourceTradingCrawler

    def fake_search(self, keyword: str):
        return self.parse_api_response(YGP_API_BODY_WITH_RESULT, keyword="钢管")

    monkeypatch.setattr(GuangdongPublicResourceTradingCrawler, "search", fake_search)
    source_config = {
        "name": "广东省公共资源交易平台 Sprint1",
        "url": "https://ygp.gdzwfw.gov.cn/ggzy-portal/",
        "source_type": "real_public_bid",
        "parser_name": "GuangdongPublicResourceTradingCrawler",
        "enabled": True,
        "province": "广东",
        "public_api_found": True,
    }

    with SessionLocal() as db:
        task = run_public_crawl(
            db,
            keyword="钢管",
            source_configs=[source_config],
            include_default_sources=False,
        )
        raw = db.scalar(select(BidRawDocument).where(BidRawDocument.source_url.like("%SPRINT1001%")))
        case = db.scalar(select(ScaffoldBidCase).where(ScaffoldBidCase.source_url.like("%SPRINT1001%")))
        review_count = db.scalar(select(func.count()).select_from(ReviewTask).where(ReviewTask.case_id == case.id)) if case else 0

    assert task.status == "success"
    assert task.total_found == 1
    assert task.total_saved >= 1
    assert raw is not None
    assert case is not None
    assert review_count >= 1


def test_blocked_source_does_not_interrupt_run_no_keyword_hits_not_failed_and_fallback_recorded(monkeypatch) -> None:
    sources = [
        SourcePlan("blocked-source", source_url="https://blocked.example", parser_name="BlockedParser", parser_status="parser_ready"),
        SourcePlan("empty-source", source_url="https://empty.example", parser_name="EmptyParser", parser_status="parser_ready"),
        SourcePlan("success-source", source_url="https://success.example", parser_name="SuccessParser", parser_status="parser_ready"),
    ]

    monkeypatch.setattr(runner, "plan", lambda config: (sources, ["脚手架"]))

    def fake_run_public_crawl(db, keyword, *, source_configs, include_default_sources, **kwargs):
        name = source_configs[0]["name"]
        if name == "blocked-source":
            return SimpleNamespace(status="failed", total_found=0, total_saved=0, error_message="blocked_403; fallback=中国政府采购网")
        if name == "empty-source":
            return SimpleNamespace(status="success", total_found=0, total_saved=0, error_message=None)
        return SimpleNamespace(status="success", total_found=2, total_saved=1, error_message=None)

    monkeypatch.setattr("app.services.crawl_service.run_public_crawl", fake_run_public_crawl)

    report = runner.run(PlanConfig(plan="national", max_sources=3, max_keywords=1, no_wecom=True, sleep_seconds=0))
    by_name = {result.source_name: result for result in report.source_results}

    assert report.status == "partial_success"
    assert by_name["blocked-source"].status == "blocked"
    assert "fallback" in (by_name["blocked-source"].blocked_reason or "")
    assert by_name["empty-source"].status == "no_match"
    assert by_name["success-source"].status == "success"
    assert report.sources_failed == 0
    assert report.sources_no_match == 1
    assert report.total_found == 2
    assert report.total_saved == 1


def test_latest_and_failures_api_data_have_flutter_required_fields(monkeypatch, client) -> None:
    sources = [
        SourcePlan("blocked-for-api", source_url="https://blocked.example", parser_name="BlockedParser", parser_status="parser_ready"),
        SourcePlan("success-for-api", source_url="https://success.example", parser_name="SuccessParser", parser_status="parser_ready"),
    ]
    monkeypatch.setattr(runner, "plan", lambda config: (sources, ["脚手架"]))

    def fake_run_public_crawl(db, keyword, *, source_configs, include_default_sources, **kwargs):
        name = source_configs[0]["name"]
        if name == "blocked-for-api":
            return SimpleNamespace(status="failed", total_found=0, total_saved=0, error_message="login_required")
        return SimpleNamespace(status="success", total_found=1, total_saved=1, error_message=None)

    monkeypatch.setattr("app.services.crawl_service.run_public_crawl", fake_run_public_crawl)
    runner.run(PlanConfig(plan="national", max_sources=2, max_keywords=1, no_wecom=True, sleep_seconds=0))

    latest = client.get("/api/crawl-orchestrator/latest")
    failures = client.get("/api/crawl-orchestrator/failures")

    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["run"]["status"] == "partial_success"
    assert latest_payload["sources"]
    for source in latest_payload["sources"]:
        for key in ("source_name", "source_url", "parser_name", "parser_status", "status", "total_found", "total_saved"):
            assert key in source

    assert failures.status_code == 200
    failure_payload = failures.json()
    assert any(item["source_name"] == "blocked-for-api" and item["blocked_reason"] == "login_required" for item in failure_payload)
