from types import SimpleNamespace

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.bid import ScaffoldBidCase
from app.models.review import ReviewTask
from app.services.crawl_service import run_public_crawl
from scripts import daily_ops_pipeline


PRICE_HTML_EMPTY = "<html><body></body></html>"


def _bid_html(suffix: str) -> str:
    return f"""
    <html><body>
    <a href="/cggg/dfgg/zbgg/202605/review-task-{suffix}.htm">广东省深圳市测试项目盘扣式脚手架租赁服务中标公告</a>
    <p>采购人：深圳市测试建设有限公司。中标金额：1200000元。发布时间：2026-05-18。</p>
    </body></html>
    """


def test_crawler_rule_extraction_creates_review_task_for_pending_case() -> None:
    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="review-task-create", price_html=PRICE_HTML_EMPTY, bid_html=_bid_html("create"))
        assert task.status == "success"

        pending_review_task = db.scalar(
            select(ReviewTask)
            .join(ScaffoldBidCase, ReviewTask.case_id == ScaffoldBidCase.id)
            .where(ScaffoldBidCase.source_url.like("%review-task-create%"))
        )
        assert pending_review_task is not None
        assert pending_review_task.status == "pending"
        assert pending_review_task.reviewer_note == "crawler generated pending case; needs manual review"


def test_repeated_crawler_run_does_not_duplicate_review_task() -> None:
    with SessionLocal() as db:
        run_public_crawl(db, keyword="review-task-dedupe", price_html=PRICE_HTML_EMPTY, bid_html=_bid_html("dedupe"))
        run_public_crawl(db, keyword="review-task-dedupe", price_html=PRICE_HTML_EMPTY, bid_html=_bid_html("dedupe"))

        count = db.scalar(
            select(func.count())
            .select_from(ReviewTask)
            .join(ScaffoldBidCase, ReviewTask.case_id == ScaffoldBidCase.id)
            .where(ScaffoldBidCase.source_url.like("%review-task-dedupe%"))
        )
        assert count == 1


def test_pending_case_remains_queryable_through_scaffold_bids_api(client) -> None:
    unique = "api-pending"
    with SessionLocal() as db:
        run_public_crawl(db, keyword=unique, price_html=PRICE_HTML_EMPTY, bid_html=_bid_html(unique))

    response = client.get("/api/scaffold/bids", params={"review_status": "pending", "keyword": "测试项目", "page_size": 100})
    assert response.status_code == 200
    data = response.json()
    assert any("测试项目" in item["project_name"] for item in data["items"])


def test_daily_ops_pipeline_report_includes_observability_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        daily_ops_pipeline,
        "_run_public_crawl_with_retry",
        lambda db, keyword, attempts, backoff_seconds: (
            SimpleNamespace(id=999, status="success", total_found=0, total_saved=0, error_message=None),
            1,
        ),
    )
    monkeypatch.setattr(daily_ops_pipeline, "extract_pending_bid_documents", lambda db, limit, use_vllm: [])
    monkeypatch.setattr(
        daily_ops_pipeline,
        "generate_today_price_summary",
        lambda db: {"date": "2026-05-18", "total_records": 0, "summary_text": "暂无", "anomalies": []},
    )
    monkeypatch.setattr(daily_ops_pipeline, "send_daily_briefing", lambda *args, **kwargs: SimpleNamespace(status="success", error_message=None))
    monkeypatch.setattr(daily_ops_pipeline, "alert_for_bid_case", lambda *args, **kwargs: None)
    monkeypatch.setattr(daily_ops_pipeline, "_vllm_available", lambda: False)

    report = daily_ops_pipeline.run_pipeline(use_vllm=False, pending_limit=1)

    for field in [
        "raw_documents_total",
        "raw_documents_pending_for_ai",
        "raw_documents_linked_to_cases",
        "scaffold_cases_pending_review",
        "review_tasks_total",
        "vllm_available",
    ]:
        assert field in report
    assert report["vllm_available"] is False
