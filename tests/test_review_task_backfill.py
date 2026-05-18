from decimal import Decimal

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference
from app.models.review import ReviewTask
from app.services.bid_service import backfill_review_tasks_for_pending_cases


def _case(source_suffix: str, confidence: str, review_status: str) -> ScaffoldBidCase:
    return ScaffoldBidCase(
        project_name=f"历史回填测试-{source_suffix}",
        source_url=f"https://example.test/review-backfill/{source_suffix}",
        extraction_confidence=Decimal(confidence),
        review_status=review_status,
        missing_fields=[],
        raw_evidence_snippets=[],
    )


def _clear_bid_cases(db) -> None:
    db.execute(delete(ReviewTask))
    db.execute(delete(ScaffoldPriceReference))
    db.execute(delete(ScaffoldBidCase))
    db.commit()


def _pending_task_count(db, case_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ReviewTask)
            .where(ReviewTask.case_id == case_id, ReviewTask.status == "pending")
        )
        or 0
    )


def test_backfill_creates_missing_review_tasks_for_historical_pending_cases() -> None:
    with SessionLocal() as db:
        _clear_bid_cases(db)
        case = _case("creates-missing", "0.90", "pending")
        db.add(case)
        db.commit()

        result = backfill_review_tasks_for_pending_cases(db)
        db.commit()

        assert result == {"scanned": 1, "created": 1, "skipped": 0}
        assert _pending_task_count(db, case.id) == 1


def test_backfill_is_idempotent_and_does_not_duplicate_pending_tasks() -> None:
    with SessionLocal() as db:
        _clear_bid_cases(db)
        case = _case("idempotent", "0.90", "pending")
        db.add(case)
        db.flush()
        db.add(ReviewTask(case_id=case.id, status="pending", reviewer_note="already queued"))
        db.commit()

        first = backfill_review_tasks_for_pending_cases(db)
        second = backfill_review_tasks_for_pending_cases(db)
        db.commit()

        assert first == {"scanned": 1, "created": 0, "skipped": 1}
        assert second == {"scanned": 1, "created": 0, "skipped": 1}
        assert _pending_task_count(db, case.id) == 1


def test_backfill_counts_created_and_skipped_for_pending_or_low_confidence_cases() -> None:
    with SessionLocal() as db:
        _clear_bid_cases(db)
        pending_without_task = _case("counts-pending", "0.95", "pending")
        low_conf_without_task = _case("counts-low-confidence", "0.69", "auto_extracted")
        pending_with_task = _case("counts-skipped", "0.80", "pending")
        irrelevant = _case("counts-irrelevant", "0.95", "auto_extracted")
        db.add_all([pending_without_task, low_conf_without_task, pending_with_task, irrelevant])
        db.flush()
        db.add(ReviewTask(case_id=pending_with_task.id, status="pending", reviewer_note="already queued"))
        db.commit()

        result = backfill_review_tasks_for_pending_cases(db, confidence_threshold=0.70)
        db.commit()

        assert result == {"scanned": 3, "created": 2, "skipped": 1}
        assert _pending_task_count(db, pending_without_task.id) == 1
        assert _pending_task_count(db, low_conf_without_task.id) == 1
        assert _pending_task_count(db, pending_with_task.id) == 1
        assert _pending_task_count(db, irrelevant.id) == 0
