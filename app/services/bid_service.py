from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference
from app.models.review import ReviewTask
from app.services.price_reference_service import replace_reference_for_case


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def list_bid_cases(db: Session, province: str | None = None, scaffold_type: str | None = None) -> list[ScaffoldBidCase]:
    stmt = select(ScaffoldBidCase)
    if province:
        stmt = stmt.where(ScaffoldBidCase.province == province)
    if scaffold_type:
        stmt = stmt.where(ScaffoldBidCase.scaffold_type == scaffold_type)
    return list(db.scalars(stmt.order_by(ScaffoldBidCase.publish_date.desc().nullslast(), ScaffoldBidCase.id.desc()).limit(100)))


def get_bid_case(db: Session, case_id: int) -> ScaffoldBidCase | None:
    return db.scalar(
        select(ScaffoldBidCase)
        .options(selectinload(ScaffoldBidCase.price_references))
        .where(ScaffoldBidCase.id == case_id)
    )


def list_price_references(db: Session, region: str | None = None, scaffold_type: str | None = None) -> list[ScaffoldPriceReference]:
    stmt = select(ScaffoldPriceReference)
    if region:
        stmt = stmt.where(ScaffoldPriceReference.region == region)
    if scaffold_type:
        stmt = stmt.where(ScaffoldPriceReference.scaffold_type == scaffold_type)
    return list(db.scalars(stmt.order_by(ScaffoldPriceReference.created_at.desc()).limit(100)))


def create_or_update_case_from_extraction(
    db: Session,
    extraction: dict[str, Any],
    source_url: str,
    raw_document_id: int | None = None,
) -> ScaffoldBidCase:
    case = db.scalar(select(ScaffoldBidCase).where(ScaffoldBidCase.source_url == source_url))
    if case is None:
        case = ScaffoldBidCase(project_name=extraction.get("project_name") or "未命名脚手架公告", source_url=source_url)
        db.add(case)

    case.raw_document_id = raw_document_id
    case.project_name = extraction.get("project_name") or case.project_name
    case.province = extraction.get("province")
    case.city = extraction.get("city")
    case.district = extraction.get("district")
    case.buyer = extraction.get("buyer")
    case.agency = extraction.get("agency")
    case.winner = extraction.get("winner")
    case.bid_amount = _decimal_or_none(extraction.get("bid_amount"))
    case.announcement_type = extraction.get("announcement_type")
    case.scaffold_type = extraction.get("scaffold_type")
    case.procurement_type = extraction.get("procurement_type")
    case.service_scope = extraction.get("service_scope")
    case.duration_text = extraction.get("duration_text")
    case.quantity_text = extraction.get("quantity_text")
    case.area_m2 = _decimal_or_none(extraction.get("area_m2"))
    case.tonnage = _decimal_or_none(extraction.get("tonnage"))
    case.rental_days = extraction.get("rental_days")
    case.pricing_method = extraction.get("pricing_method")
    case.publish_date = _parse_date(extraction.get("publish_date"))
    case.ai_summary = extraction.get("ai_summary")
    case.extraction_confidence = _decimal_or_none(extraction.get("confidence")) or Decimal("0.0")
    db.flush()
    replace_reference_for_case(db, case)
    db.flush()
    return case


def review_case(db: Session, case_id: int, status: str, reviewer_note: str | None) -> ReviewTask | None:
    case = db.get(ScaffoldBidCase, case_id)
    if case is None:
        return None
    case.review_status = status
    task = ReviewTask(case_id=case_id, status=status, reviewer_note=reviewer_note)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
