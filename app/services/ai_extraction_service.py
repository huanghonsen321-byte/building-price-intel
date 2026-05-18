from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.extractor import extract_scaffold_bid_sync
from app.models.crawl import BidRawDocument
from app.models.review import ReviewTask
from app.services.bid_service import create_or_update_case_from_extraction


def _ensure_review_task(db: Session, case_id: int, note: str) -> None:
    existing = db.scalar(select(ReviewTask).where(ReviewTask.case_id == case_id, ReviewTask.status == "pending"))
    if existing is None:
        db.add(ReviewTask(case_id=case_id, status="pending", reviewer_note=note))


def extract_pending_bid_documents(
    db: Session,
    limit: int = 20,
    use_vllm: bool = True,
    confidence_threshold: Decimal = Decimal("0.70"),
):
    raw_documents = list(
        db.scalars(
            select(BidRawDocument)
            .outerjoin(BidRawDocument.bid_case)
            .where(BidRawDocument.bid_case == None)  # noqa: E711
            .order_by(BidRawDocument.publish_date.desc().nullslast(), BidRawDocument.id.desc())
            .limit(limit)
        )
    )
    cases = []
    for raw in raw_documents:
        extraction = extract_scaffold_bid_sync(raw.text_content, source_url=raw.source_url, use_vllm=use_vllm)
        if not extraction.get("project_name"):
            extraction["project_name"] = raw.title
        if not extraction.get("publish_date") and raw.publish_date:
            extraction["publish_date"] = raw.publish_date.isoformat()
        case = create_or_update_case_from_extraction(
            db,
            extraction=extraction,
            source_url=raw.source_url,
            raw_document_id=raw.id,
        )
        confidence = Decimal(str(case.extraction_confidence or 0))
        if confidence < confidence_threshold or case.missing_fields:
            case.review_status = "pending"
            _ensure_review_task(
                db,
                case.id,
                f"AI 抽取置信度 {confidence}，缺失字段：{', '.join(case.missing_fields or []) or '无'}",
            )
        cases.append(case)
    db.commit()
    for case in cases:
        db.refresh(case)
    return cases
