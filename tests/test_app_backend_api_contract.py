from __future__ import annotations

import re
from pathlib import Path

from app.main import app


REPO_ROOT = Path(__file__).resolve().parents[1]
API_CLIENT = REPO_ROOT / "mobile" / "flutter_app" / "lib" / "api_client.dart"


def _route_table() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path.startswith("/api"):
            for method in methods:
                if method not in {"HEAD", "OPTIONS"}:
                    routes.add((method, path))
    return routes


def _flutter_api_calls() -> list[tuple[str, str]]:
    content = API_CLIENT.read_text()
    calls: list[tuple[str, str]] = []
    for method, path in re.findall(r"dio\.(get|post|put|delete|patch)\(\s*'([^']+)'", content):
        normalized = re.sub(r"\$\w+", "{id}", path)
        normalized = re.sub(r"\$\{[^}]+\}", "{id}", normalized)
        calls.append((method.upper(), normalized))
    return calls


def _path_matches_route(client_path: str, route_path: str) -> bool:
    client_parts = client_path.strip("/").split("/")
    route_parts = route_path.strip("/").split("/")
    if len(client_parts) != len(route_parts):
        return False
    for client_part, route_part in zip(client_parts, route_parts, strict=True):
        if client_part.startswith("{") and client_part.endswith("}"):
            if not (route_part.startswith("{") and route_part.endswith("}")):
                return False
        elif route_part.startswith("{") and route_part.endswith("}"):
            continue
        elif client_part != route_part:
            return False
    return True


def test_flutter_api_client_paths_exist_in_fastapi_routes() -> None:
    routes = _route_table()
    missing = []
    for method, path in _flutter_api_calls():
        if not any(route_method == method and _path_matches_route(path, route_path) for route_method, route_path in routes):
            missing.append((method, path))
    assert missing == []


def test_expected_app_backend_routes_exist() -> None:
    routes = _route_table()
    expected = {
        ("GET", "/api/health"),
        ("GET", "/api/prices/today"),
        ("GET", "/api/prices/today/summary"),
        ("GET", "/api/prices"),
        ("GET", "/api/prices/trends"),
        ("GET", "/api/scaffold/bids"),
        ("GET", "/api/scaffold/bids/{case_id}"),
        ("GET", "/api/scaffold/prices/reference"),
        ("POST", "/api/scaffold/bids/extract-pending"),
        ("POST", "/api/quote/scaffold/calculate"),
        ("GET", "/api/attachments"),
        ("GET", "/api/attachments/{attachment_id}"),
        ("POST", "/api/attachments/parse-pending"),
        ("POST", "/api/notifications/daily-briefing/send"),
        ("GET", "/api/notifications/logs"),
    }
    missing = sorted(expected - routes)
    assert missing == []
    assert ("GET", "/api/pricing/regional-prices") not in routes



def test_prices_today_summary_returns_flutter_required_fields(client) -> None:
    response = client.get("/api/prices/today/summary")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"date", "total_records", "summary_text", "regions", "anomalies", "updated_at"}


def test_scaffold_bids_pending_returns_page_contract(client) -> None:
    response = client.get("/api/scaffold/bids", params={"review_status": "pending", "page": 1, "page_size": 20})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"items", "total", "page", "page_size"}
    assert isinstance(payload["items"], list)
    assert payload["page"] == 1
    assert payload["page_size"] == 20


def test_regional_prices_endpoint_absence_matches_flutter_contract() -> None:
    routes = _route_table()
    flutter_paths = {path for _, path in _flutter_api_calls()}
    assert ("GET", "/api/pricing/regional-prices") not in routes
    assert "/api/pricing/regional-prices" not in flutter_paths



def test_optional_operation_endpoints_return_app_parseable_shapes(client) -> None:
    notifications = client.get("/api/notifications/logs?page=1&page_size=20")
    assert notifications.status_code == 200
    notification_payload = notifications.json()
    assert set(notification_payload) >= {"items", "total", "page", "page_size"}
    assert isinstance(notification_payload["items"], list)
    assert isinstance(notification_payload["total"], int)
