import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "app/crawlers/config/sources_national_v4.json"
RUNNER_PATH = ROOT / "scripts/run_national_public_crawl_v4.sh"


def test_national_v4_config_is_bounded_and_compliant() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    limits = config["limits"]

    assert limits["concurrency"] <= 4
    assert limits["request_delay_seconds"] >= 1
    assert limits["max_keywords_per_run"] <= 12
    assert limits["max_sources_per_run"] <= 6
    assert "respect" in limits["robots_policy"]

    all_sources = config["price_sources"] + config["bid_sources"]
    assert any(source["enabled"] for source in all_sources)
    assert all("proxy" not in json.dumps(source, ensure_ascii=False).lower() for source in all_sources)
    assert all(source["type"] != "unlimited" for source in all_sources)


def test_national_v4_keywords_cover_scaffold_and_materials() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    keywords = set(config["keywords"])

    assert "脚手架" in keywords
    assert "盘扣式脚手架" in keywords
    assert "周转材料租赁" in keywords
    assert "钢管租赁" in keywords
    assert "模板支撑" in keywords


def test_national_v4_dry_run_does_not_touch_network_or_database() -> None:
    result = subprocess.run(
        [str(RUNNER_PATH), "--dry-run", "--max-keywords", "2"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert "Dry-run only" in result.stdout
    assert "脚手架,盘扣" in result.stdout
