"""Compliant public browser discovery helpers.

This module is intentionally conservative: it only observes publicly rendered pages
and public XHR/fetch responses. It never stores cookies, authorization headers, or
query/body token values. When a source presents 403/captcha/login/paid content,
discovery stops and reports the blocked reason instead of bypassing it.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_HEADER_NAMES = {"cookie", "set-cookie", "authorization", "proxy-authorization", "x-api-key", "x-auth-token"}
SENSITIVE_KEY_RE = re.compile(r"(token|cookie|session|sid|auth|credential|password|secret|key)", re.I)
BLOCKED_STATUS = {"blocked_403", "captcha_required", "login_required", "paid_content"}


@dataclass
class BrowserDiscoveryResult:
    source_name: str
    page_url: str
    public_page_reachable: bool = False
    public_api_found: bool = False
    api_url: str | None = None
    status: str = "transport_error"
    response_status: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str | None = None
    fixture_path: str | None = None


def sanitize_url(url: str | None) -> str | None:
    if not url:
        return url
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not SENSITIVE_KEY_RE.search(k)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def sanitize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if key.lower() in SENSITIVE_HEADER_NAMES or SENSITIVE_KEY_RE.search(key):
            continue
        clean[key] = value
    return clean


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_payload(v) for k, v in value.items() if not SENSITIVE_KEY_RE.search(str(k))}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)(token|cookie|session|sid|auth|secret|key)=([^&\s\"]+)", r"\1=<redacted>", value)
    return value


def sanitize_response_body(body: str | None) -> str | None:
    if body is None:
        return None
    try:
        parsed = json.loads(body)
    except Exception:
        return str(_sanitize_payload(body))
    return json.dumps(_sanitize_payload(parsed), ensure_ascii=False, indent=2)


def save_public_response_fixture(result: BrowserDiscoveryResult, fixture_dir: str | Path) -> Path:
    fixture_dir = Path(fixture_dir)
    fixture_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", result.source_name).strip("_") or "source"
    path = fixture_dir / f"{safe_name}_public_response.json"
    payload = asdict(result)
    payload["api_url"] = sanitize_url(result.api_url)
    payload["response_headers"] = sanitize_headers(result.response_headers)
    payload["response_body"] = sanitize_response_body(result.response_body)
    payload["fixture_path"] = None
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result.fixture_path = str(path)
    return path


def _classify_page_text(status_code: int | None, text: str) -> str | None:
    lower = (text or "").lower()
    if status_code == 403:
        return "blocked_403"
    if any(token in lower for token in ("captcha", "验证码", "滑块验证", "人机验证")):
        return "captcha_required"
    if any(token in lower for token in ("登录", "登陆", "login", "sign in", "password")) and ("password" in lower or "登录" in lower or "login" in lower):
        return "login_required"
    if any(token in lower for token in ("付费", "会员", "订阅", "paywall", "paid content")):
        return "paid_content"
    return None


def discover_public_browser_api(source_name: str, page_url: str, fixture_dir: str | Path) -> BrowserDiscoveryResult:
    """Render a public page and save the first public JSON/list response fixture.

    Playwright is imported lazily so normal crawler tests/runs do not require it.
    The browser context does not persist storage state, and saved fixtures are
    sanitized by `save_public_response_fixture`.
    """

    result = BrowserDiscoveryResult(source_name=source_name, page_url=page_url)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        result.status = "transport_error"
        result.response_body = f"Playwright unavailable: {exc}"
        return result

    with sync_playwright() as p:  # pragma: no cover - exercised manually/integration
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state={})
        page = context.new_page()
        public_responses: list[Any] = []

        def on_response(response: Any) -> None:
            request = response.request
            if request.resource_type not in {"xhr", "fetch"}:
                return
            ctype = response.headers.get("content-type", "")
            if "json" in ctype or any(marker in response.url.lower() for marker in ("api", "search", "list", "query")):
                public_responses.append(response)

        page.on("response", on_response)
        try:
            response = page.goto(page_url, wait_until="networkidle", timeout=20000)
            result.response_status = response.status if response else None
            page_text = page.content()
            result.public_page_reachable = bool(response and response.status < 400)
            blocked = _classify_page_text(result.response_status, page_text)
            if blocked:
                result.status = blocked
                return result
            if not public_responses:
                result.status = "js_render_required" if result.public_page_reachable else "transport_error"
                return result
            api_response = public_responses[0]
            result.public_api_found = True
            result.status = "public_api_found"
            result.api_url = api_response.url
            result.response_status = api_response.status
            result.response_headers = dict(api_response.headers)
            result.response_body = api_response.text()
            save_public_response_fixture(result, fixture_dir)
            return result
        finally:
            context.clear_cookies()
            browser.close()
