"""Source library validator — check URL availability without bypassing restrictions."""

from __future__ import annotations

import httpx

from app.source_library.schemas import SourceEntry

USER_AGENT = "building-price-intel/0.1 (+public-data; source-library-validator)"

BLOCKED_INDICATORS = {
    "blocked_403": ["403", "forbidden", "access denied"],
    "captcha_required": ["captcha", "验证码", "滑块验证", "人机验证"],
    "login_required": ["请输入密码", "登录", "登陆", "login", "sign in", "password"],
    "paid_content": ["付费", "会员", "订阅", "paywall", "paid content", "vip"],
}


def _classify_response(status_code: int, text: str) -> str | None:
    """Check response for blocked indicators. Returns blocked_reason or None."""
    lower = text.lower()
    if status_code == 403:
        return "blocked_403"
    for reason, indicators in BLOCKED_INDICATORS.items():
        if any(indicator in lower for indicator in indicators):
            return reason
    return None


def validate_url(
    url: str,
    timeout: int = 10,
) -> dict:
    """Check if a public URL is reachable. Does NOT bypass 403/captcha/login/paywall.

    Returns: {"reachable": bool, "status_code": int, "blocked_reason": str|None, "error": str|None}
    """
    result: dict = {"reachable": False, "status_code": None, "blocked_reason": None, "error": None}
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        result["error"] = "invalid url"
        return result

    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True
        ) as client:
            response = client.get(url)
            result["status_code"] = response.status_code
            if response.status_code < 400:
                result["reachable"] = True
            blocked = _classify_response(response.status_code, response.text[:20_000])
            if blocked:
                result["blocked_reason"] = blocked
    except Exception as exc:
        result["error"] = str(exc)[:500]
    return result


def validate_source(source: SourceEntry) -> dict:
    """Validate a source entry's URL.

    Returns dict with validation results and any errors from schema validation.
    """
    from app.source_library.schemas import validate_source_entry

    errors = validate_source_entry(source)
    result: dict = {
        "name": source.name,
        "schema_valid": len(errors) == 0,
        "schema_errors": errors,
        "url_result": None,
    }
    if source.url:
        result["url_result"] = validate_url(source.url)
    return result
