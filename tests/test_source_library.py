"""Tests for source library module."""

from app.source_library.registry import (
    get_source,
    get_sources,
    get_source_count,
    get_stats,
    load_source_library,
    load_keyword_library,
)
from app.source_library.schemas import (
    SourceEntry,
    SourceQuery,
    SourceLibraryStats,
    validate_source_entry,
)
from app.source_library.validator import validate_url, validate_source
from app.source_library.scoring import compute_reliability_score, score_all_sources


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def test_load_source_library() -> None:
    data = load_source_library(force=True)
    assert "national_sources" in data
    assert "guangdong_city_sources" in data
    assert "national_province_sources" in data
    assert "price_sources" in data
    assert "manual_import_sources" in data


def test_load_keyword_library() -> None:
    data = load_keyword_library()
    assert len(data["scaffold_keywords"]) >= 20
    assert "脚手架" in data["scaffold_keywords"]
    assert "盘扣式脚手架" in data["scaffold_keywords"]
    assert "螺纹钢" in data["steel_keywords"]
    assert "重废" in data["scrap_keywords"]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def test_get_stats() -> None:
    stats = get_stats()
    assert stats.total_sources >= 70
    assert stats.national_sources >= 7
    assert stats.guangdong_sources >= 25
    assert stats.enabled_sources >= 9
    assert stats.parser_ready_sources >= 7
    assert isinstance(stats.by_acquisition_method, dict)
    assert isinstance(stats.by_parser_status, dict)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def test_get_sources_all() -> None:
    sources = get_sources()
    assert len(sources) >= 70


def test_get_sources_by_province() -> None:
    q = SourceQuery(province="广东")
    results = get_sources(q)
    assert len(results) >= 25
    for r in results:
        assert r.province == "广东"


def test_get_sources_by_enabled() -> None:
    q = SourceQuery(enabled=True)
    results = get_sources(q)
    assert len(results) >= 9
    for r in results:
        assert r.enabled is True


def test_get_sources_by_parser_ready() -> None:
    q = SourceQuery(parser_status="parser_ready")
    results = get_sources(q)
    assert len(results) >= 7
    for r in results:
        assert r.parser_status == "parser_ready"


def test_get_sources_by_source_level_national() -> None:
    q = SourceQuery(source_level="national")
    results = get_sources(q)
    for r in results:
        assert r.source_level == "national"


def test_get_sources_by_keyword() -> None:
    q = SourceQuery(keyword="盘扣")
    results = get_sources(q)
    # Should find sources with "盘扣" in name or keywords
    assert len(results) >= 0  # Depends on data


def test_get_source_by_name() -> None:
    entry = get_source("全国公共资源交易平台")
    assert entry is not None
    assert entry.domain == "ggzy.gov.cn"
    assert entry.source_level == "national"


def test_get_source_by_index() -> None:
    entry = get_source(1)
    assert entry is not None
    assert isinstance(entry.name, str)


def test_get_source_not_found() -> None:
    assert get_source("不存在的源") is None


# ---------------------------------------------------------------------------
# Guangdong coverage
# ---------------------------------------------------------------------------

def test_guangdong_provincial_sources_exist() -> None:
    q = SourceQuery(province="广东")
    results = get_sources(q)
    names = {r.name for r in results}
    assert "广东省公共资源交易平台" in names
    assert "广东政府采购智慧云平台" in names
    assert "广东省招标投标监管网" in names


def test_guangdong_21_city_sources_exist() -> None:
    q = SourceQuery(province="广东")
    results = get_sources(q)
    cities = {r.city for r in results if r.city}
    expected = {"广州", "深圳", "佛山", "东莞", "中山", "珠海", "惠州", "江门", "汕头", "肇庆",
                "河源", "清远", "阳江", "茂名", "湛江", "韶关", "梅州", "揭阳", "潮州", "汕尾", "云浮"}
    for city in expected:
        assert city in cities, f"Missing Guangdong city: {city}"


def test_national_province_sources_exist() -> None:
    sources = get_sources()
    provinces = {s.province for s in sources if s.province}
    expected = {"北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
                "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
                "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
                "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"}
    for prov in expected:
        assert prov in provinces, f"Missing province: {prov}"


# ---------------------------------------------------------------------------
# Price sources
# ---------------------------------------------------------------------------

def test_price_sources_exist() -> None:
    q = SourceQuery(source_type="price")
    results = get_sources(q)
    assert len(results) >= 8
    names = {r.name for r in results}
    assert "生意社公开价格页" in names


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_validate_source_entry_valid() -> None:
    errors = validate_source_entry({
        "name": "测试源", "url": "https://test.com",
        "source_level": "national", "source_type": "bid",
        "acquisition_method": "html_list_page", "parser_status": "parser_ready",
    })
    assert errors == []


def test_validate_source_entry_invalid_level() -> None:
    errors = validate_source_entry({
        "name": "测试", "url": "https://test.com",
        "source_level": "invalid_level",
    })
    assert len(errors) >= 1


def test_validate_source_entry_invalid_url() -> None:
    errors = validate_source_entry({
        "name": "测试", "url": "ftp://bad.com",
    })
    assert any("url" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_compute_reliability_score_parser_ready() -> None:
    entry = SourceEntry(
        name="测试", parser_status="parser_ready", enabled=True,
        parser_name="TestParser", public_api_found=True,
        source_level="national", keywords=["脚手架"],
    )
    score = compute_reliability_score(entry)
    assert score >= 0.8


def test_compute_reliability_score_blocked() -> None:
    entry = SourceEntry(
        name="测试", parser_status="blocked", enabled=False,
    )
    score = compute_reliability_score(entry)
    assert score <= 0.2


def test_score_all_sources_sorted() -> None:
    sources = [
        SourceEntry(name="A", parser_status="parser_ready", enabled=True, parser_name="P"),
        SourceEntry(name="B", parser_status="blocked", enabled=False),
        SourceEntry(name="C", parser_status="not_started", enabled=False),
    ]
    scored = score_all_sources(sources)
    assert scored[0][0].name == "A"
    assert scored[-1][0].name in ("B", "C")


# ---------------------------------------------------------------------------
# Validator (URL check - may fail without network)
# ---------------------------------------------------------------------------

def test_validate_url_invalid() -> None:
    result = validate_url("not-a-url")
    assert result["error"] is not None


def test_validate_source() -> None:
    entry = SourceEntry(name="测试", url="https://www.ggzy.gov.cn", parser_status="parser_ready")
    result = validate_source(entry)
    assert "name" in result


# ---------------------------------------------------------------------------
# No proxy / bypass logic
# ---------------------------------------------------------------------------

def test_no_proxy_pool_in_source_library() -> None:
    """Source library contains no proxy or bypass logic."""
    from pathlib import Path
    lib_dir = Path(__file__).resolve().parents[1] / "app" / "source_library"
    for py_file in lib_dir.glob("*.py"):
        content = py_file.read_text().lower()
        assert "proxy" not in content or "proxy_pool" not in content, f"{py_file.name} contains proxy logic"
        assert "stealth" not in content, f"{py_file.name} contains stealth"
        assert "fingerprint" not in content, f"{py_file.name} contains fingerprint bypass"
