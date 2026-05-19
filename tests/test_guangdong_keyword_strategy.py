"""Tests for Guangdong two-layer keyword strategy."""

from app.crawlers.guangdong_keyword_strategy import (
    CORE_KEYWORDS,
    DISCOVERY_KEYWORDS,
    DISCOVERY_CONTEXT_WORDS,
    EXCLUDED_KEYWORDS,
    NEGATIVE_KEYWORDS,
    classify_keyword,
    get_all_keyword_info,
    get_core_keywords,
    get_discovery_keywords,
    get_guangdong_plan_keywords,
    is_negative_hit,
    should_include_discovery_result,
    should_include_result,
)


def test_pankou_not_in_core_but_in_discovery() -> None:
    assert "盘扣" not in CORE_KEYWORDS
    assert "盘扣" in DISCOVERY_KEYWORDS
    assert classify_keyword("盘扣") == "discovery"


def test_gangguan_is_discovery_keyword() -> None:
    assert "钢管" in DISCOVERY_KEYWORDS
    assert classify_keyword("钢管") == "discovery"


def test_precise_scaffold_keywords_are_core() -> None:
    assert "盘扣式脚手架" in CORE_KEYWORDS
    assert "扣件式脚手架" in CORE_KEYWORDS
    assert "钢管脚手架" in CORE_KEYWORDS
    assert classify_keyword("盘扣式脚手架") == "core"


def test_broad_generic_keywords_are_excluded() -> None:
    for keyword in ["工程材料", "建筑材料", "租赁", "工程"]:
        assert keyword in EXCLUDED_KEYWORDS
        assert classify_keyword(keyword) == "excluded"
        assert should_include_result(keyword, f"{keyword}采购项目") is False


def test_negative_false_positive_terms_are_filtered() -> None:
    for title in ["田边村盘岭3号商铺出租", "盘龙花园售楼部", "楼盘开盘促销", "椎间盘突出手术", "地名盘信息"]:
        assert is_negative_hit(title) is True
        assert should_include_result("盘扣", title) is False


def test_precise_pankou_scaffold_rental_is_kept() -> None:
    assert should_include_result("盘扣式脚手架", "盘扣式脚手架租赁服务") is True
    assert should_include_result("脚手架", "盘扣式脚手架租赁服务") is True


def test_discovery_gangguan_rental_project_is_kept() -> None:
    assert should_include_result("钢管", "钢管租赁项目招标公告") is True
    assert should_include_discovery_result("钢管", "钢管采购工程中标候选人公示") is True


def test_discovery_keyword_without_context_is_excluded() -> None:
    assert should_include_discovery_result("钢管", "钢管") is False
    assert should_include_result("钢管", "钢管") is False


def test_discovery_context_words_match_expected_contract() -> None:
    for word in ["脚手架", "租赁", "支撑", "钢管", "扣件", "模板", "周转材料", "架体", "搭拆", "工程", "采购", "招标", "中标", "施工"]:
        assert word in DISCOVERY_CONTEXT_WORDS


def test_guangdong_plan_keywords_reserve_discovery_tail() -> None:
    keywords = get_guangdong_plan_keywords(8)
    assert len(keywords) == 8
    assert keywords[0] == "脚手架"
    assert "盘扣式脚手架" in keywords
    assert "盘扣" not in keywords[:6]
    assert "钢管" in keywords
    assert "盘扣" in keywords


def test_core_and_discovery_getters_are_separate() -> None:
    assert get_core_keywords() == CORE_KEYWORDS
    assert get_discovery_keywords() == DISCOVERY_KEYWORDS
    assert set(get_core_keywords()).isdisjoint({"盘扣", "钢管", "模板"})


def test_keyword_info_structure() -> None:
    info = get_all_keyword_info()
    assert info["total_core"] == len(CORE_KEYWORDS)
    assert info["total_discovery"] == len(DISCOVERY_KEYWORDS)
    assert info["total_excluded"] == len(EXCLUDED_KEYWORDS)
    assert info["total_negative"] == len(NEGATIVE_KEYWORDS)
    assert info["core_keywords"] == CORE_KEYWORDS
    assert info["discovery_keywords"] == DISCOVERY_KEYWORDS
    assert info["excluded_keywords"] == EXCLUDED_KEYWORDS


def test_core_keywords_only_need_negative_filter() -> None:
    assert should_include_result("钢管脚手架", "钢管脚手架搭拆工程") is True
    assert should_include_result("钢管脚手架", "盘岭钢管脚手架项目") is False
