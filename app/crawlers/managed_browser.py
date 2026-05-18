"""Managed browser collection for authorized public pages.

Compliance-first: only visits allowlisted domains, never saves cookies or
tokens, never bypasses captcha/login/403/paywall. Audit trail via
ManagedBrowserRun records.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.managed_browser_run import ManagedBrowserRun

USER_AGENT = "building-price-intel/0.1 (+public-data; managed-browser)"
CONFIG_DIR = Path(__file__).resolve().parent / "config"
ALLOWLIST_PATH = CONFIG_DIR / "browser_allowlist.json"

BLOCKED_INDICATORS: dict[str, re.Pattern] = {
    "blocked_403": re.compile(r"(?i)403|forbidden|access denied"),
    "captcha_required": re.compile(r"(?i)captcha|验证码|滑块验证|人机验证"),
    "login_required": re.compile(r"(?i)(请输入|密码|password|login|sign.?in|登录|登陆)"),
    "paid_content": re.compile(r"(?i)(付费|会员|订阅|paywall|paid content|vip)"),
}

MAX_VISITED_URLS = 50
DOWNLOAD_TIMEOUT = 30_000  # ms


@dataclass
class BrowserCollectorConfig:
    source_key: str
    keyword: str
    mode: str = "dry-run"  # dry-run | run | manual-login
    download_attachments: bool = False
    headless: bool = True
    max_results: int = 20


@dataclass
class BrowserRunResult:
    source_name: str = ""
    keyword: str = ""
    mode: str = "dry-run"
    visited_urls: list[str] = field(default_factory=list)
    downloaded_files: list[str] = field(default_factory=list)
    records_created: int = 0
    attachments_created: int = 0
    blocked_reason: str | None = None
    error_message: str | None = None


def load_allowlist() -> dict:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def is_domain_allowed(url: str, allowlist: list[str] | None = None) -> bool:
    if allowlist is None:
        allowlist = load_allowlist().get("allowlist", [])
    hostname = urlparse(url).hostname or ""
    return any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in allowlist
    )


def classify_blocked_page(text: str) -> str | None:
    """Check page text for blocked indicators."""
    for reason, pattern in BLOCKED_INDICATORS.items():
        if pattern.search(text[:20_000]):
            return reason
    return None


def _save_run_record(db: Session, result: BrowserRunResult) -> ManagedBrowserRun:
    run = ManagedBrowserRun(
        source_name=result.source_name,
        keyword=result.keyword,
        mode=result.mode,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        visited_urls=result.visited_urls,
        downloaded_files=result.downloaded_files,
        records_created=result.records_created,
        attachments_created=result.attachments_created,
        blocked_reason=result.blocked_reason,
        error_message=result.error_message,
    )
    db.add(run)
    db.flush()
    return run


def dry_run_collect(config: BrowserCollectorConfig) -> BrowserRunResult:
    """Dry-run: validate config and report planned actions, no network, no DB."""
    allowlist_data = load_allowlist()
    source_map = allowlist_data.get("source_mappings", {}).get(config.source_key)

    if source_map is None:
        return BrowserRunResult(
            source_name=config.source_key,
            keyword=config.keyword,
            mode="dry-run",
            error_message=f"Unknown source key: {config.source_key}",
        )

    source_name = source_map["name"]
    search_url = source_map["search_url"]
    allowed = source_map.get("allowed_domains", [])
    strategy = source_map.get("search_strategy", "html_page")

    return BrowserRunResult(
        source_name=source_name,
        keyword=config.keyword,
        mode="dry-run",
        visited_urls=[f"[planned] {search_url}"],
    )


def live_collect(
    config: BrowserCollectorConfig,
    db: Session,
) -> BrowserRunResult:
    """Run live collection using Playwright, within allowlist boundaries.

    Does NOT:
    - Bypass 403/captcha/login/paywall
    - Save cookies/tokens/sessions
    - Visit non-allowlisted domains
    """
    allowlist_data = load_allowlist()
    source_map = allowlist_data.get("source_mappings", {}).get(config.source_key)

    if source_map is None:
        return BrowserRunResult(
            source_name=config.source_key,
            keyword=config.keyword,
            mode=config.mode,
            error_message=f"Unknown source key: {config.source_key}",
        )

    source_name = source_map["name"]
    search_url = source_map["search_url"]
    allowed_domains = source_map.get("allowed_domains", [])
    global_allowlist = allowlist_data.get("allowlist", [])
    all_allowed = list(set(global_allowlist + allowed_domains))

    result = BrowserRunResult(
        source_name=source_name,
        keyword=config.keyword,
        mode=config.mode,
    )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.error_message = "Playwright not installed"
        _save_run_record(db, result)
        return result

    page = None
    browser = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=config.headless)
            context = browser.new_context(
                storage_state={},  # fresh context, no cookies
                user_agent=USER_AGENT,
            )
            page = context.new_page()

            # Step 1: Navigate to search page
            result.visited_urls.append(search_url)

            if not is_domain_allowed(search_url, all_allowed):
                result.blocked_reason = "domain_not_allowed"
                _save_run_record(db, result)
                return result

            response = page.goto(search_url, wait_until="networkidle", timeout=20_000)

            # Step 2: Check for blocked indicators
            page_text = page.content()
            blocked = classify_blocked_page(page_text)
            if blocked:
                result.blocked_reason = blocked
                _save_run_record(db, result)
                return result

            # Step 3: Try keyword search via public form or navigation
            strategy = source_map.get("search_strategy", "html_page")
            found_links = _execute_search_strategy(
                page, config.keyword, strategy, source_map, all_allowed
            )

            # Step 4: Visit result links and extract content
            announce_links = found_links[: config.max_results]
            for link_url in announce_links:
                if len(result.visited_urls) >= MAX_VISITED_URLS:
                    break
                if not is_domain_allowed(link_url, all_allowed):
                    continue

                result.visited_urls.append(link_url)
                try:
                    page.goto(link_url, wait_until="networkidle", timeout=15_000)
                    detail_text = page.content()
                    blocked = classify_blocked_page(detail_text)
                    if blocked:
                        result.blocked_reason = blocked
                        break

                    # Save to DB
                    record = _save_bid_from_browser(
                        db, source_name, link_url, detail_text
                    )
                    if record:
                        result.records_created += 1

                    # Download attachments if enabled
                    if config.download_attachments:
                        att_count = _download_attachments_from_page(
                            page, db, record, link_url, all_allowed
                        )
                        result.attachments_created += att_count
                except Exception:
                    continue

            _save_run_record(db, result)
            return result

    except Exception as exc:
        result.error_message = str(exc)[:2000]
        _save_run_record(db, result)
        return result
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass


def _execute_search_strategy(
    page, keyword: str, strategy: str, source_map: dict, allowlist: list[str]
) -> list[str]:
    """Execute a search on the page and return result link URLs."""
    links: list[str] = []

    try:
        if strategy == "homepage_listing":
            # Parse homepage for announcement links (ggzy.gov.cn pattern)
            import re as _re
            content = page.content()
            pattern = _re.compile(r"/information/(?:deal|html)/html/a/\d{6}/")
            for a in page.query_selector_all("a[href]"):
                href = a.get_attribute("href") or ""
                if pattern.search(href) and keyword in (a.inner_text() or ""):
                    full_url = _resolve_url(href, page.url)
                    if is_domain_allowed(full_url, allowlist):
                        links.append(full_url)

        elif strategy == "search_form":
            # Fill search form (ccgp.gov.cn pattern)
            search_params = source_map.get("search_params", {})
            page.goto(source_map["search_url"], wait_until="networkidle", timeout=15_000)
            # Try typing keyword into a search input
            search_input = page.query_selector(
                'input[type="text"], input[name*="kw"], input[name*="search"], input[name*="keyword"]'
            )
            if search_input:
                search_input.fill(keyword)
                search_btn = page.query_selector(
                    'input[type="submit"], button[type="submit"], button:has-text("搜索"), input[value*="搜索"]'
                )
                if search_btn:
                    search_btn.click()
                    page.wait_for_timeout(3000)
            content = page.content()
            links = _extract_links_from_html(content, page.url, allowlist)

        elif strategy == "spa_navigate":
            # SPA: try keyword search via URL hash or input
            content = page.content()
            # Try finding a search input
            search_input = page.query_selector(
                'input[placeholder*="搜索"], input[type="text"], input[name*="search"]'
            )
            if search_input:
                search_input.fill(keyword)
                page.keyboard.press("Enter")
                page.wait_for_timeout(3000)
                content = page.content()
            links = _extract_links_from_html(content, page.url, allowlist)

        else:  # html_page
            content = page.content()
            links = _extract_links_from_html(content, page.url, allowlist)

    except Exception:
        pass

    return list(dict.fromkeys(links))  # dedupe preserving order


def _extract_links_from_html(html: str, base_url: str, allowlist: list[str]) -> list[str]:
    """Extract keyword-relevant links from rendered HTML."""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    scaffold_keywords = ["脚手架", "盘扣", "钢管", "扣件", "周转材料", "模板", "爬架", "租赁", "中标", "招标"]

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = str(a.get("href", "") or "")
        text = a.get_text(" ", strip=True)
        combined = f"{text} {href}"

        if any(kw in combined for kw in scaffold_keywords):
            full = urljoin(base_url, href)
            if is_domain_allowed(full, allowlist) and full not in seen:
                seen.add(full)
                links.append(full)

    return links


def _resolve_url(href: str, base_url: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base_url, href)


def _save_bid_from_browser(
    db: Session, source_name: str, url: str, html_content: str
) -> bool:
    """Save browser-rendered page as a bid_raw_document."""
    from bs4 import BeautifulSoup
    import hashlib
    from app.models.crawl import BidRawDocument

    existing = db.scalar(select(BidRawDocument).where(BidRawDocument.source_url == url))
    if existing is not None:
        return False

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url
    text = soup.get_text("\n", strip=True)[:100_000]

    content_hash = hashlib.sha256(f"{url}\n{text}".encode()).hexdigest()

    raw = BidRawDocument(
        source_name=source_name,
        source_url=url,
        title=title[:512],
        text_content=text,
        html_content=html_content[:500_000],
        content_hash=content_hash,
        crawl_status="saved",
    )
    db.add(raw)
    db.flush()
    return True


def _download_attachments_from_page(
    page, db: Session, raw_doc, page_url: str, allowlist: list[str]
) -> int:
    """Find and download attachment links from a rendered page."""
    from app.services.attachment_extractor import (
        discover_attachment_links,
        process_attachment,
    )

    html = page.content()
    links = discover_attachment_links(html, page_url)
    count = 0
    for file_url, _label in links:
        if not is_domain_allowed(file_url, allowlist):
            continue
        try:
            process_attachment(
                db,
                file_url=file_url,
                raw_document_id=raw_doc.id if raw_doc else None,
                source_url=page_url,
            )
            count += 1
        except Exception:
            pass
    return count


def manual_login_collect(
    config: BrowserCollectorConfig, db: Session
) -> BrowserRunResult:
    """Open browser for manual login, then proceed with collection."""
    allowlist_data = load_allowlist()
    source_map = allowlist_data.get("source_mappings", {}).get(config.source_key)

    if source_map is None:
        return BrowserRunResult(
            source_name=config.source_key,
            keyword=config.keyword,
            mode="manual-login",
            error_message=f"Unknown source key: {config.source_key}",
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return BrowserRunResult(
            error_message="Playwright not installed",
            mode="manual-login",
        )

    page = None
    browser = None
    result = BrowserRunResult(
        source_name=source_map["name"],
        keyword=config.keyword,
        mode="manual-login",
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state={})
            page = context.new_page()

            search_url = source_map["search_url"]
            result.visited_urls.append(search_url)

            page.goto(search_url, wait_until="networkidle", timeout=30_000)
            print(f"\n=== MANUAL LOGIN REQUIRED ===")
            print(f"Source: {source_map['name']}")
            print(f"URL: {search_url}")
            print("Please log in manually in the browser window.")
            print("Press Enter in this terminal when ready to continue...")
            input()

            # After login, proceed with collection
            results_config = BrowserCollectorConfig(
                source_key=config.source_key,
                keyword=config.keyword,
                mode="run",
                download_attachments=config.download_attachments,
                headless=False,  # stay visible
                max_results=config.max_results,
            )
            result = live_collect(results_config, db)

    except Exception as exc:
        result.error_message = str(exc)[:2000]
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return result


def list_runs(db: Session, limit: int = 20) -> list[ManagedBrowserRun]:
    return list(
        db.scalars(
            select(ManagedBrowserRun)
            .order_by(ManagedBrowserRun.created_at.desc())
            .limit(limit)
        )
    )


def get_run(db: Session, run_id: int) -> ManagedBrowserRun | None:
    return db.get(ManagedBrowserRun, run_id)
