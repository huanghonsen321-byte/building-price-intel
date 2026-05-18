from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.crawlers.browser_discovery import BrowserDiscoveryResult, save_public_response_fixture
from app.crawlers.real_public_sources import (
    BlockedReason,
    BlockedSourceError,
    classify_blocked_response,
)
from app.models.crawl import CrawlSource, CrawlTask
from app.services import crawl_service
from app.services.crawl_service import build_crawl_dashboard_summary, run_public_crawl


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", url: str = "https://blocked.example/search") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("blocked", request=httpx.Request("GET", str(self.url)), response=httpx.Response(self.status_code))


def test_403_is_recorded_as_blocked_without_retry_or_bypass(monkeypatch) -> None:
    calls = {"blocked": 0, "total": 0}

    def fake_get(self, *args, **kwargs):
        calls["total"] += 1
        if args and str(args[0]).startswith("https://blocked.example"):
            calls["blocked"] += 1
        return FakeResponse(403, "Forbidden")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    source_config = {
        "name": "合规测试403源",
        "url": "https://blocked.example/search",
        "source_type": "bid",
        "parser_name": "ChinaGovernmentProcurementCrawler",
        "province": "全国",
        "enabled": True,
    }

    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="脚手架", price_html="<html></html>", source_configs=[source_config], include_default_sources=False)
        source = db.scalar(select(CrawlSource).where(CrawlSource.name == "合规测试403源"))

    assert calls["blocked"] == 1
    assert task.status == "failed"
    assert task.error_message and "blocked_403" in task.error_message
    assert source is not None
    assert source.last_blocked_reason == "blocked_403"
    assert source.requires_manual_review is True


def test_captcha_page_is_recorded_as_captcha_required_without_continuing(monkeypatch) -> None:
    calls = {"captcha": 0, "total": 0}

    def fake_get(self, *args, **kwargs):
        calls["total"] += 1
        if args and str(args[0]).startswith("https://captcha.example"):
            calls["captcha"] += 1
        return FakeResponse(200, "请完成验证码后继续访问")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with SessionLocal() as db:
        task = run_public_crawl(
            db,
            keyword="脚手架",
            price_html="<html></html>",
            source_configs=[{"name": "合规测试验证码源", "url": "https://captcha.example", "source_type": "bid", "parser_name": "ChinaGovernmentProcurementCrawler", "enabled": True}],
            include_default_sources=False,
        )
        source = db.scalar(select(CrawlSource).where(CrawlSource.name == "合规测试验证码源"))

    assert calls["captcha"] == 1
    assert task.status == "failed"
    assert source is not None
    assert source.last_blocked_reason == "captcha_required"
    assert source.requires_manual_review is True


def test_login_page_is_recorded_as_login_required() -> None:
    response = FakeResponse(200, "<html><title>用户登录</title><form><input type='password'></form></html>")

    reason = classify_blocked_response(response)

    assert reason == BlockedReason.LOGIN_REQUIRED


def test_browser_discovery_fixture_does_not_save_cookie_or_token(tmp_path: Path) -> None:
    result = BrowserDiscoveryResult(
        source_name="公开测试源",
        page_url="https://public.example/list",
        public_page_reachable=True,
        public_api_found=True,
        api_url="https://public.example/api/list?keyword=脚手架&token=SECRET",
        status="public_api_found",
        response_status=200,
        response_headers={"content-type": "application/json", "set-cookie": "sid=SECRET", "authorization": "Bearer SECRET"},
        response_body='{"items":[],"access_token":"SECRET","cookie":"sid=SECRET"}',
    )

    fixture_path = save_public_response_fixture(result, tmp_path)
    content = fixture_path.read_text(encoding="utf-8")

    assert "SECRET" not in content
    assert "set-cookie" not in content.lower()
    assert "authorization" not in content.lower()
    assert "token=" not in content.lower()
    assert "access_token" not in content.lower()
    assert "public_api_found" in content


def test_fallback_sources_continue_after_blocked_primary(monkeypatch) -> None:
    class AlwaysBlockedCrawler:
        source_name = "合规测试主源403"
        base_url = "https://blocked.example/search"

        def search(self, keyword: str):
            raise BlockedSourceError(BlockedReason.BLOCKED_403)

        def parse_search_results(self, html: str, keyword: str, base_url: str | None = None):
            raise BlockedSourceError(BlockedReason.BLOCKED_403)

    monkeypatch.setitem(crawl_service.BID_CRAWLER_REGISTRY, "AlwaysBlockedCrawler", AlwaysBlockedCrawler)
    primary = {
        "name": "合规测试主源403",
        "url": "https://blocked.example/search",
        "source_type": "bid",
        "parser_name": "AlwaysBlockedCrawler",
        "enabled": True,
        "fallbacks": [
            {
                "name": "合规测试fallback中国政府采购网",
                "url": "http://search.ccgp.gov.cn/bxsearch",
                "source_type": "bid",
                "parser_name": "ChinaGovernmentProcurementCrawler",
                "enabled": True,
            }
        ],
    }
    fallback_html = """
    <html><body>
    <a href="/cggg/dfgg/zbgg/202605/t_fallback.htm">广东省学校盘扣式脚手架租赁服务中标公告</a>
    <p>中标金额：1200000元。发布时间：2026-05-18。</p>
    </body></html>
    """

    with SessionLocal() as db:
        task = run_public_crawl(
            db,
            keyword="脚手架",
            price_html="<html></html>",
            source_configs=[primary],
            bid_html_by_parser={"ChinaGovernmentProcurementCrawler": fallback_html},
            include_default_sources=False,
        )
        primary_source = db.scalar(select(CrawlSource).where(CrawlSource.name == "合规测试主源403"))
        fallback_source = db.scalar(select(CrawlSource).where(CrawlSource.name == "合规测试fallback中国政府采购网"))

    assert task.status == "success"
    assert task.total_found == 1
    assert primary_source is not None and primary_source.last_blocked_reason == "blocked_403"
    assert fallback_source is not None and fallback_source.last_success_at is not None


def test_dashboard_summary_includes_blocked_and_regional_success_metrics() -> None:
    with SessionLocal() as db:
        gd_ok = CrawlSource(name="合规测试广东可用源", base_url="https://gd.example", source_type="bid", parser_status="ok", last_success_at=datetime.now(UTC))
        gd_blocked = CrawlSource(name="合规测试广东403源", base_url="https://gd-blocked.example", source_type="bid", last_blocked_reason="blocked_403", requires_manual_review=True)
        national_ok = CrawlSource(name="合规测试全国可用源", base_url="https://national.example", source_type="bid", parser_status="ok", last_success_at=datetime.now(UTC))
        db.add_all([gd_ok, gd_blocked, national_ok])
        db.flush()
        db.add_all([
            CrawlTask(source_id=gd_ok.id, keyword="脚手架", status="success", started_at=datetime.now(UTC), finished_at=datetime.now(UTC), total_found=1, total_saved=1),
            CrawlTask(source_id=gd_blocked.id, keyword="脚手架", status="blocked", started_at=datetime.now(UTC), finished_at=datetime.now(UTC), total_found=0, total_saved=0, error_message="blocked_403"),
            CrawlTask(source_id=national_ok.id, keyword="脚手架", status="success", started_at=datetime.now(UTC), finished_at=datetime.now(UTC), total_found=1, total_saved=1),
        ])
        db.commit()

        summary = build_crawl_dashboard_summary(db)

    assert summary["blocked_source_count"] >= 1
    assert summary["blocked_reason_distribution"]["blocked_403"] >= 1
    assert summary["available_source_count"] >= 2
    assert summary["today_successful_source_count"] >= 2
    assert 0 < summary["guangdong_success_rate"] <= 1
    assert 0 < summary["national_success_rate"] <= 1
