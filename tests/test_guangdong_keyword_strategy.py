"""Tests for Guangdong keyword strategy module.

Verifies:
1. "盘扣" is not in core keywords
2. "盘扣式脚手架" is in core keywords
3. Combination queries are available
4. "盘岭" in title → negative hit
5. "盘扣式脚手架租赁" in title → included
6. "工程材料", "模板", "租赁" not as solo production keywords
7. get_guangdong_production_keywords excludes high-noise words
8. should_include_result filters false positives
"""

import pytest
from app.crawlers.guangdong_keyword_strategy import (
    CORE_KEYWORDS,
    COMBINATION_KEYWORDS,
    EXCLUDED_SINGLE_KEYWORDS,
    classify_guangdong_keyword,
    get_guangdong_combination_queries,
    get_guangdong_production_keywords,
    get_all_keyword_info,
    is_negative_hit,
    is_relevant_guangdong_hit,
    should_include_result,
)


# === Test 1: "盘扣" alone should NOT be in core keywords ===
def test_pankou_not_in_core():
    assert "盘扣" not in CORE_KEYWORDS, "盘扣 should not be in CORE_KEYWORDS (too many false positives)"


# === Test 2: "盘扣式脚手架" should be in core keywords ===
def test_pankou_shaojia_in_core():
    assert "盘扣式脚手架" in CORE_KEYWORDS, "盘扣式脚手架 should be in CORE_KEYWORDS"


# === Test 3: Classification works correctly ===
def test_classify_guangdong_keyword():
    assert classify_guangdong_keyword("脚手架") == "core"
    assert classify_guangdong_keyword("盘扣式脚手架") == "core"
    assert classify_guangdong_keyword("盘扣") == "excluded"
    assert classify_guangdong_keyword("模板") == "excluded"
    assert classify_guangdong_keyword("工程材料") == "excluded"
    assert classify_guangdong_keyword("租赁") == "excluded"
    assert classify_guangdong_keyword("建筑材料") == "excluded"
    assert classify_guangdong_keyword("支架") == "excluded"
    assert classify_guangdong_keyword("random") == "unknown"


# === Test 4: Negative hit detection ===
def test_negative_hit_detection():
    # "盘岭" is a place name, should be negative
    assert is_negative_hit("田边村盘岭3号商铺出租") is True
    assert is_negative_hit("盘岭太和路厂房出租") is True
    assert is_negative_hit("盘龙花园售楼部") is True
    assert is_negative_hit("楼盘开盘促销") is True
    assert is_negative_hit("椎间盘突出手术") is True

    # Not negative
    assert is_negative_hit("盘扣式脚手架租赁服务") is False
    assert is_negative_hit("钢管脚手架搭拆工程") is False
    assert is_negative_hit("扣件租赁价格表") is False


# === Test 5: Relevance check for "盘扣" ===
def test_pankou_without_context_is_irrelevant():
    # "盘扣" alone with place name → irrelevant
    assert is_relevant_guangdong_hit("盘扣", "田边村盘岭3号厂房出租") is False
    assert is_relevant_guangdong_hit("盘扣", "盘岭太和路简易厂房出租") is False

    # "盘扣" with context word → relevant
    assert is_relevant_guangdong_hit("盘扣", "盘扣式脚手架租赁服务") is True
    assert is_relevant_guangdong_hit("盘扣", "盘扣钢管支撑架采购") is True
    assert is_relevant_guangdong_hit("盘扣", "盘扣扣件出租") is True


# === Test 6: Title with "盘扣式脚手架租赁" should be included ===
def test_pankou_shaojia_zulin_included():
    assert should_include_result("盘扣式脚手架", "盘扣式脚手架租赁服务") is True
    assert should_include_result("脚手架", "盘扣式脚手架租赁服务") is True


# === Test 7: "工程材料", "模板", "租赁" not as solo keywords ===
def test_excluded_keywords_not_as_solo():
    for kw in ["工程材料", "模板", "租赁", "建筑材料", "支架", "盘扣"]:
        assert kw in EXCLUDED_SINGLE_KEYWORDS, f"{kw} should be excluded"


# === Test 8: get_guangdong_production_keywords excludes noise words ===
def test_production_keywords_excludes_noise():
    production = get_guangdong_production_keywords()
    noise_words = ["盘扣", "模板", "工程材料", "租赁", "建筑材料", "支架"]
    for word in noise_words:
        assert word not in production, f"{word} should not be in production keywords"


# === Test 9: should_include_result filters false positives ===
def test_should_include_filters_false_positives():
    # Place name hits should be excluded
    assert should_include_result("盘扣", "田边村盘岭3号厂房出租") is False
    assert should_include_result("盘扣", "盘岭太和路简易厂房出租") is False
    assert should_include_result("盘扣", "盘岭3号综合楼出租") is False

    # Real scaffolding hits should be included
    assert should_include_result("盘扣式脚手架", "盘扣式脚手架租赁") is True
    assert should_include_result("脚手架", "钢管脚手架搭拆工程") is True

    # Excluded keyword should always return False
    assert should_include_result("工程材料", "钢材采购") is False
    assert should_include_result("租赁", "设备租赁服务") is False
    assert should_include_result("模板", "混凝土模板采购") is False


# === Test 10: Combination queries are available ===
def test_combination_queries_available():
    queries = get_guangdong_combination_queries()
    # Should have at least the defined combinations
    assert len(queries) >= 8

    # Check specific combinations
    queries_dict = {(q["primary"], q["secondary"]) for q in queries}
    assert ("盘扣", "脚手架") in queries_dict
    assert ("盘扣", "租赁") in queries_dict
    assert ("盘扣", "支撑") in queries_dict
    assert ("钢管", "租赁") in queries_dict
    assert ("钢管", "扣件") in queries_dict
    assert ("模板", "支撑") in queries_dict
    assert ("模板", "脚手架") in queries_dict
    assert ("周转材料", "租赁") in queries_dict


# === Test 11: get_all_keyword_info returns valid structure ===
def test_keyword_info_structure():
    info = get_all_keyword_info()
    assert info["total_core"] == 12
    assert info["total_combination"] == 8
    assert info["total_excluded"] == 6
    assert "core_keywords" in info
    assert "combination_keywords" in info
    assert "excluded_keywords" in info
    assert "negative_keywords" in info
    assert "ambiguous_context" in info


# === Test 12: Core keywords are all classification-safe ===
def test_all_core_keywords_safe():
    for kw in CORE_KEYWORDS:
        assert classify_guangdong_keyword(kw) == "core", f"{kw} should classify as core"


# === Test 13: Negative keywords don't affect core keyword results ===
def test_negative_keywords_dont_false_positive_core():
    # Even core keywords shouldn't trigger negative hits normally
    assert is_negative_hit("脚手架采购") is False
    assert is_negative_hit("盘扣式脚手架") is False
    assert is_negative_hit("钢管租赁") is False
    assert is_negative_hit("扣件式脚手架出租") is False
