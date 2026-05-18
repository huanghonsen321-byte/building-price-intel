from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.bid import ReviewRequest, ScaffoldBidCaseDetail, ScaffoldBidCaseOut, ScaffoldPriceReferenceOut
from app.schemas.pagination import Page
from app.services.ai_extraction_service import extract_pending_bid_documents
from app.services.bid_service import get_bid_case, list_bid_cases, list_price_references, review_case

router = APIRouter(prefix="/api/scaffold", tags=["scaffold"])


@router.get("/bids", response_model=Page[ScaffoldBidCaseOut])
def get_scaffold_bids(
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    scaffold_type: str | None = None,
    procurement_type: str | None = None,
    review_status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_bid_cases(
        db,
        keyword=keyword,
        province=province,
        city=city,
        scaffold_type=scaffold_type,
        procurement_type=procurement_type,
        review_status=review_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/bids/extract-pending", response_model=list[ScaffoldBidCaseOut])
def post_extract_pending_bids(
    limit: int = Query(default=20, ge=1, le=100),
    use_vllm: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return extract_pending_bid_documents(db, limit=limit, use_vllm=use_vllm)


@router.get("/bids/{case_id}", response_model=ScaffoldBidCaseDetail)
def get_scaffold_bid(case_id: int, db: Session = Depends(get_db)):
    case = get_bid_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="bid case not found")
    return case


@router.get("/prices/reference", response_model=Page[ScaffoldPriceReferenceOut])
def get_scaffold_price_references(
    region: str | None = None,
    scaffold_type: str | None = None,
    calculated_unit: str | None = None,
    confidence: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = list_price_references(
        db,
        region=region,
        scaffold_type=scaffold_type,
        calculated_unit=calculated_unit,
        confidence=confidence,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/bids/{case_id}/review")
def post_scaffold_bid_review(case_id: int, payload: ReviewRequest, db: Session = Depends(get_db)):
    task = review_case(db, case_id=case_id, status=payload.status, reviewer_note=payload.reviewer_note)
    if task is None:
        raise HTTPException(status_code=404, detail="bid case not found")
    return {"id": task.id, "case_id": task.case_id, "status": task.status, "reviewer_note": task.reviewer_note}
