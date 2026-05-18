from datetime import datetime
from pathlib import Path

import pytest

from app.core.database import SessionLocal
from app.crawlers.managed_browser import (
    BrowserCollectorConfig,
    BrowserRunResult,
    _save_run_record,
    classify_blocked_page,
    dry_run_collect,
    is_domain_allowed,
    load_allowlist,
    _extract_links_from_html,
    _save_bid_from_browser,
)
from app.models.managed_browser_run import ManagedBrowserRun

# ---------------------------------------------------------------------------
# Allowlist tests
# ---------------------------------------------------------------------------

def test_load_allowlist() -> None:
    data = load_allowlist()
    assert "allowlist" in data
    assert "source_mappings" in data
    assert "ggzy.gov.cn" in data["allowlist"]
    assert "ygp" in data["source_mappings"]


def test_is_domain_allowed_exact_match() -> None:
    allowed = ["ggzy.gov.cn", "gzggzy.cn"]
    assert is_domain_allowed("https://www.ggzy.gov.cn/page", allowed)
    assert is_domain_allowed("http://ggzy.gov.cn/info", allowed)
    assert not is_domain_allowed("https://evil.com/page", allowed)


def test_is_domain_allowed_subdomain() -> None:
    allowed = ["ggzy.gov.cn", "gzggzy.cn"]
    assert is_domain_allowed("https://sub.ggzy.gov.cn/page", allowed)
    assert is_domain_allowed("https://ywtb.gzggzy.cn/page", allowed)


def test_is_domain_allowed_blocks_non_allowlisted() -> None:
    allowed = ["ggzy.gov.cn"]
    assert not is_domain_allowed("https://evil.ggzy.gov.cn.evil.com", allowed)
    assert not is_domain_allowed("https://other-site.com/ggzy.gov.cn", allowed)


# ---------------------------------------------------------------------------
# Blocked page classification
# ---------------------------------------------------------------------------

def test_classify_403_page() -> None:
    assert classify_blocked_page("403 Forbidden") == "blocked_403"
    assert classify_blocked_page("Access Denied") == "blocked_403"


def test_classify_captcha_page() -> None:
    assert classify_blocked_page("请输入验证码") == "captcha_required"
    assert classify_blocked_page("滑块验证") == "captcha_required"
    assert classify_blocked_page("captcha required") == "captcha_required"


def test_classify_login_page() -> None:
    assert classify_blocked_page("请输入密码") == "login_required"
    assert classify_blocked_page("请登录后查看") == "login_required"
    assert classify_blocked_page("sign in to continue") == "login_required"


def test_classify_paid_page() -> None:
    assert classify_blocked_page("付费会员可查看") == "paid_content"
    assert classify_blocked_page("paywall content") == "paid_content"


def test_classify_normal_page() -> None:
    assert classify_blocked_page("公告内容 脚手架租赁 中标金额 100万元") is None
    assert classify_blocked_page("<html><body>招标公告</body></html>") is None


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

def test_dry_run_valid_source() -> None:
    config = BrowserCollectorConfig(source_key="ygp", keyword="脚手架", mode="dry-run")
    result = dry_run_collect(config)
    assert result.mode == "dry-run"
    assert result.source_name == "广东省公共资源交易平台"
    assert result.error_message is None


def test_dry_run_invalid_source() -> None:
    config = BrowserCollectorConfig(source_key="invalid_source", keyword="test", mode="dry-run")
    result = dry_run_collect(config)
    assert result.error_message is not None
    assert "Unknown source" in result.error_message


def test_dry_run_does_not_write_db() -> None:
    with SessionLocal() as db:
        before = len(db.query(ManagedBrowserRun).all())
        config = BrowserCollectorConfig(source_key="ygp", keyword="脚手架", mode="dry-run")
        dry_run_collect(config)  # dry-run, no DB writes
        after = len(db.query(ManagedBrowserRun).all())
        assert after == before


# ---------------------------------------------------------------------------
# Link extraction from HTML
# ---------------------------------------------------------------------------

BID_LISTING_HTML = """
<html><body>
<ul>
<li><a href="/bid/12345.html">广州市盘扣式脚手架租赁中标公告</a></li>
<li><a href="/bid/12346.html">深圳市钢管扣件采购成交结果公告</a></li>
<li><a href="/bid/12347.html">办公设备采购公告</a></li>
<li><a href="/bid/12348.html">佛山市模板脚手架专业分包招标公告</a></li>
</ul>
</body></html>
"""


def test_extract_links_filters_by_keyword() -> None:
    allowed = ["ggzy.gov.cn"]
    links = _extract_links_from_html(
        BID_LISTING_HTML, "https://www.ggzy.gov.cn/", allowed
    )
    assert len(links) == 3  # 脚手架, 钢管扣件, 模板脚手架 (not 办公设备)
    assert any("12345" in l for l in links)  # 盘扣式脚手架
    assert any("12346" in l for l in links)  # 钢管扣件
    assert any("12348" in l for l in links)  # 模板脚手架


def test_extract_links_rejects_non_allowlisted_domains() -> None:
    html = '<a href="https://evil.com/bid/1">脚手架招标</a>'
    allowed = ["ggzy.gov.cn"]
    links = _extract_links_from_html(html, "https://ggzy.gov.cn", allowed)
    assert links == []


def test_extract_links_deduplicates() -> None:
    html = """
    <a href="/bid/1">脚手架招标</a>
    <a href="/bid/1">脚手架招标 (重复)</a>
    """
    allowed = ["ggzy.gov.cn"]
    links = _extract_links_from_html(html, "https://ggzy.gov.cn", allowed)
    assert len(links) == 1


# ---------------------------------------------------------------------------
# Save bid from browser
# ---------------------------------------------------------------------------

def test_save_bid_from_browser() -> None:
    with SessionLocal() as db:
        html = "<html><head><title>盘扣脚手架中标公告</title></head><body><p>中标金额：500万元</p></body></html>"
        result = _save_bid_from_browser(
            db, "测试源", "https://test.local/bid/1", html
        )
        assert result is True

        # Duplicate should be False
        result2 = _save_bid_from_browser(
            db, "测试源", "https://test.local/bid/1", html
        )
        assert result2 is False


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def test_save_run_record() -> None:
    with SessionLocal() as db:
        result = BrowserRunResult(
            source_name="测试源",
            keyword="脚手架",
            mode="run",
            visited_urls=["https://test.local/page1"],
            downloaded_files=["https://test.local/file.pdf"],
            records_created=5,
            attachments_created=2,
        )
        run = _save_run_record(db, result)
        assert run.id is not None
        assert run.source_name == "测试源"
        assert run.keyword == "脚手架"
        assert run.mode == "run"
        assert len(run.visited_urls) == 1
        assert len(run.downloaded_files) == 1
        assert run.records_created == 5
        assert run.attachments_created == 2


def test_save_blocked_run() -> None:
    with SessionLocal() as db:
        result = BrowserRunResult(
            source_name="测试源",
            keyword="脚手架",
            mode="run",
            blocked_reason="captcha_required",
        )
        run = _save_run_record(db, result)
        assert run.blocked_reason == "captcha_required"


# ---------------------------------------------------------------------------
# Browser collector config
# ---------------------------------------------------------------------------

def test_browser_collector_config_defaults() -> None:
    config = BrowserCollectorConfig(source_key="ygp", keyword="脚手架")
    assert config.source_key == "ygp"
    assert config.keyword == "脚手架"
    assert config.mode == "dry-run"
    assert config.download_attachments is False
    assert config.headless is True
    assert config.max_results == 20
