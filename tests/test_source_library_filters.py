"""Filter consistency tests for source library API.

Verifies that source_level, province, parser_status, and enabled filters
return correct counts after the fix for category-derived source_level.
"""

from app.source_library.registry import (
    get_sources,
    get_stats,
    load_source_library,
)
from app.source_library.schemas import SourceQuery


def setup_function():
    load_source_library(force=True)


# ---------------------------------------------------------------------------
# source_level tests
# ---------------------------------------------------------------------------

def test_source_level_national_returns_seven() -> None:
    q = SourceQuery(source_level="national")
    results = get_sources(q)
    assert len(results) == 7, f"Expected 7 national sources, got {len(results)}"
    names = {r.name for r in results}
    assert "全国公共资源交易平台" in names
    assert "中国政府采购网" in names
    assert "中央政府采购网" in names
    assert "中国招标投标公共服务平台" in names
    assert "中国招标投标网" in names
    assert "央企采购公开公告平台" in names


def test_source_level_province_has_correct_count() -> None:
    q = SourceQuery(source_level="province")
    results = get_sources(q)
    assert len(results) >= 35, f"Expected >=35 province-level sources, got {len(results)}"
    # Province-level sources should include both Guangdong provincial and national provinces
    provinces = {r.province for r in results if r.province}
    assert "广东" in provinces
    assert "北京" in provinces or any(r.province == "北京" for r in results)


def test_source_level_city_returns_21_guangdong_cities() -> None:
    q = SourceQuery(source_level="city")
    results = get_sources(q)
    assert len(results) == 21, f"Expected 21 city sources, got {len(results)}"
    cities = {r.city for r in results if r.city}
    expected = {"广州", "深圳", "佛山", "东莞", "中山", "珠海", "惠州", "江门",
                "汕头", "肇庆", "河源", "清远", "阳江", "茂名", "湛江",
                "韶关", "梅州", "揭阳", "潮州", "汕尾", "云浮"}
    for city in expected:
        assert city in cities, f"Missing city: {city}"
    for r in results:
        assert r.source_level == "city", f"Expected city source_level, got {r.source_level} for {r.name}"


# ---------------------------------------------------------------------------
# province tests
# ---------------------------------------------------------------------------

def test_province_guangdong_returns_twenty_six() -> None:
    """广东 = 5 provincial + 21 cities = 26"""
    q = SourceQuery(province="广东")
    results = get_sources(q)
    assert len(results) == 26, f"Expected 26 Guangdong sources, got {len(results)}"
    for r in results:
        assert r.province == "广东", f"{r.name} province={r.province}"

    # Verify both provincial and city are present
    levels = {r.source_level for r in results}
    assert "province" in levels
    assert "city" in levels


def test_province_guangdong_cities_are_present() -> None:
    """All 21 Guangdong cities should appear in the province filter."""
    q = SourceQuery(province="广东", source_level="city")
    results = get_sources(q)
    assert len(results) == 21
    cities = {r.city for r in results}
    for city in ("广州", "深圳", "佛山", "东莞", "中山", "珠海", "惠州", "江门",
                 "汕头", "肇庆", "河源", "清远", "阳江", "茂名", "湛江",
                 "韶关", "梅州", "揭阳", "潮州", "汕尾", "云浮"):
        assert city in cities


# ---------------------------------------------------------------------------
# parser_status tests
# ---------------------------------------------------------------------------

def test_parser_status_parser_ready_returns_eight() -> None:
    q = SourceQuery(parser_status="parser_ready")
    results = get_sources(q)
    assert len(results) == 8, f"Expected 8 parser_ready sources, got {len(results)}"
    names = {r.name for r in results}
    expected = {
        "全国公共资源交易平台", "中国政府采购网", "中央政府采购网",
        "中国招标投标公共服务平台", "广东省公共资源交易平台",
        "广东政府采购智慧云平台", "广州公共资源交易平台", "生意社公开价格页",
    }
    assert names == expected


def test_parser_status_not_started_is_majority() -> None:
    q = SourceQuery(parser_status="not_started")
    results = get_sources(q)
    assert len(results) >= 60, f"Expected >=60 not_started sources, got {len(results)}"


# ---------------------------------------------------------------------------
# enabled tests
# ---------------------------------------------------------------------------

def test_enabled_true_returns_nine() -> None:
    q = SourceQuery(enabled=True)
    results = get_sources(q)
    assert len(results) == 9, f"Expected 9 enabled sources, got {len(results)}"
    for r in results:
        assert r.enabled is True


# ---------------------------------------------------------------------------
# Combined filter tests
# ---------------------------------------------------------------------------

def test_guangdong_parser_ready_returns_three() -> None:
    """广东 enabled+parser_ready: 广东省/广东政务云/广州"""
    q = SourceQuery(province="广东", parser_status="parser_ready")
    results = get_sources(q)
    assert len(results) == 3, f"Expected 3 Guangdong parser_ready, got {len(results)}"
    names = {r.name for r in results}
    assert names == {
        "广东省公共资源交易平台",
        "广东政府采购智慧云平台",
        "广州公共资源交易平台",
    }


def test_national_parser_ready_returns_four() -> None:
    """National parser_ready: ggzy, ccgp, zycg, ctbpsp = 4"""
    q = SourceQuery(source_level="national", parser_status="parser_ready")
    results = get_sources(q)
    assert len(results) == 4, f"Expected 4 national parser_ready, got {len(results)}"
    for r in results:
        assert r.source_level == "national"
        assert r.parser_status == "parser_ready"
    names = {r.name for r in results}
    assert names == {"全国公共资源交易平台", "中国政府采购网", "中央政府采购网", "中国招标投标公共服务平台"}


def test_province_guangdong_enabled_false_source_count() -> None:
    """Disabled Guangdong sources should be 23 (26 total - 3 enabled)."""
    q = SourceQuery(province="广东", enabled=False)
    results = get_sources(q)
    assert len(results) == 23


# ---------------------------------------------------------------------------
# Stats consistency
# ---------------------------------------------------------------------------

def test_stats_match_filters() -> None:
    """Stats numbers should match filtered query counts."""
    stats = get_stats()

    assert stats.total_sources == 76
    assert stats.national_sources == len(get_sources(SourceQuery(source_level="national")))
    assert stats.province_source_count == len(get_sources(SourceQuery(source_level="province")))
    assert stats.city_source_count == len(get_sources(SourceQuery(source_level="city")))
    assert stats.guangdong_sources == len(get_sources(SourceQuery(province="广东")))
    assert stats.parser_ready_sources == len(get_sources(SourceQuery(parser_status="parser_ready")))
    assert stats.enabled_sources == len(get_sources(SourceQuery(enabled=True)))
    assert stats.guangdong_parser_ready_sources == len(get_sources(SourceQuery(province="广东", parser_status="parser_ready")))


def test_dry_run_matched_equals_api_province_count() -> None:
    """dry-run --province 广东 matched=26 should equal API province=广东 count."""
    q = SourceQuery(province="广东")
    api_count = len(get_sources(q))
    assert api_count == 26, f"API province=广东 returns {api_count}, expected 26 (dry-run matched)"


def test_every_source_has_valid_level() -> None:
    """Every flattened source should have a valid source_level."""
    valid = {"national", "province", "city", "price", "manual", "authorized", "enterprise", "industry"}
    for s in get_sources():
        assert s.source_level in valid, f"{s.name} has invalid source_level: {s.source_level}"


def test_source_level_never_defaults_to_national_for_province_or_city() -> None:
    """Province and city category sources must NOT have source_level=national."""
    for s in get_sources():
        if s.province and s.source_level == "national":
            # Only true national sources should have this
            assert s.name in {
                "全国公共资源交易平台", "全国公共资源交易平台数据服务",
                "中国政府采购网", "中央政府采购网",
                "中国招标投标公共服务平台", "中国招标投标网",
                "央企采购公开公告平台",
            }, f"{s.name} has source_level=national but is not a true national source"
