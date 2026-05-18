import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.crawlers.real_public_sources import GuangdongPublicResourceTradingCrawler
from app.models.bid import ScaffoldBidCase
from app.models.crawl import BidRawDocument
from app.models.review import ReviewTask
from app.services.crawl_service import run_public_crawl

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "app/crawlers/config/sources_national_v4.json"
RUNNER_PATH = ROOT / "scripts/run_national_public_crawl_v4.sh"

GUANGDONG_PIPELINE_HTML = """
<html><body>
<div class="notice-item">
<a href="/ggzy-portal/#/44/jygg/details?id=gd-pipeline-001">佛山市顺德区学校盘扣式脚手架租赁项目中标候选人公示</a>
<span>交易类型：工程建设</span><span>发布日期：2026-05-17</span>
<p>广东省佛山市，采购脚手架、周转材料租赁服务，中标金额：218.6万元。服务期：90天。</p>
</div>
</body></html>
"""


def _delete_test_records() -> None:
    with SessionLocal() as db:
        raw_ids = list(
            db.scalars(
                select(BidRawDocument.id).where(
                    BidRawDocument.source_url.like("%gd-pipeline-001%")
                )
            )
        )
        case_ids = list(
            db.scalars(select(ScaffoldBidCase.id).where(ScaffoldBidCase.source_url.like("%gd-pipeline-001%")))
        )
        for case_id in case_ids:
            db.query(ReviewTask).filter(ReviewTask.case_id == case_id).delete(synchronize_session=False)
        db.query(ScaffoldBidCase).filter(ScaffoldBidCase.id.in_(case_ids)).delete(synchronize_session=False)
        db.query(BidRawDocument).filter(BidRawDocument.id.in_(raw_ids)).delete(synchronize_session=False)
        db.commit()


def test_guangdong_parser_can_parse_sample_notice() -> None:
    crawler = GuangdongPublicResourceTradingCrawler()
    docs = crawler.parse_search_results(GUANGDONG_PIPELINE_HTML, keyword="脚手架")

    assert len(docs) == 1
    assert docs[0].source_name == "广东省公共资源交易平台"
    assert docs[0].region == "广东"
    assert "218.6万元" in docs[0].text_content


def test_guangdong_parser_results_flow_into_raw_cases_and_review_queue() -> None:
    _delete_test_records()
    source_config = {
        "name": "广东省公共资源交易平台",
        "url": "https://ygp.gdzwfw.gov.cn/ggzy-portal/#/44/index",
        "source_type": "bid",
        "parser_name": "GuangdongPublicResourceTradingCrawler",
        "province": "广东",
        "enabled": True,
    }

    with SessionLocal() as db:
        first = run_public_crawl(
            db,
            keyword="脚手架",
            source_configs=[source_config],
            bid_html_by_parser={"GuangdongPublicResourceTradingCrawler": GUANGDONG_PIPELINE_HTML},
            include_default_sources=False,
        )
        second = run_public_crawl(
            db,
            keyword="脚手架",
            source_configs=[source_config],
            bid_html_by_parser={"GuangdongPublicResourceTradingCrawler": GUANGDONG_PIPELINE_HTML},
            include_default_sources=False,
        )

        raw_count = db.scalar(select(func.count()).select_from(BidRawDocument).where(BidRawDocument.source_url.like("%gd-pipeline-001%")))
        case = db.scalar(select(ScaffoldBidCase).where(ScaffoldBidCase.source_url.like("%gd-pipeline-001%")))
        review_count = db.scalar(select(func.count()).select_from(ReviewTask).where(ReviewTask.case_id == case.id)) if case else 0

    assert first.status == "success"
    assert first.total_saved == 1
    assert second.status == "success"
    assert second.total_saved == 0
    assert raw_count == 1
    assert case is not None
    assert case.raw_document_id is not None
    assert case.province == "广东"
    assert case.review_status == "pending"
    assert case.extraction_confidence < 0.70
    assert review_count == 1


def test_v4_runner_dry_run_guangdong_mode_does_not_write_database_or_push(tmp_path: Path) -> None:
    db_path = tmp_path / "dry_run_should_not_exist.db"
    env = os.environ.copy()
    env["BUILDING_PRICE_INTEL_PYTHON"] = str(ROOT / ".venv/bin/python")
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["BUILDING_PRICE_INTEL_DB"] = str(db_path)
    env["WECOM_WEBHOOK_URL"] = ""

    result = subprocess.run(
        [str(RUNNER_PATH), "--dry-run", "--province", "广东", "--max-keywords", "3", "--max-sources", "3"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert "Dry-run only" in result.stdout
    assert "广东省公共资源交易平台" in result.stdout
    assert "广东政府采购智慧云平台" in result.stdout
    assert "广州公共资源交易平台" in result.stdout
    assert not db_path.exists()


def test_guangdong_config_enables_first_three_sources_only() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    gd_sources = [source for source in config["bid_sources"] if source.get("province") == "广东" or "广东" in source.get("regions", [])]
    enabled = {source["name"] for source in gd_sources if source.get("enabled") is True}

    assert {
        "广东省公共资源交易平台",
        "广东政府采购智慧云平台",
        "广州公共资源交易平台",
    }.issubset(enabled)
    assert all(
        source.get("enabled") is False
        for source in gd_sources
        if source["name"] not in enabled and source.get("city") not in (None, "广州")
    )
