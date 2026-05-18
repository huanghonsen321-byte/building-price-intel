from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.bid import ReviewRequest, ScaffoldBidCaseDetail, ScaffoldBidCaseOut, ScaffoldPriceReferenceOut
from app.services.bid_service import get_bid_case, list_bid_cases, list_price_references, review_case

router = APIRouter(prefix="/api/scaffold", tags=["scaffold"])


@router.get("/bids", response_model=list[ScaffoldBidCaseOut])
def get_scaffold_bids(
    province: str | None = None,
    scaffold_type: str | None = None,
    db: Session = Depends(get_db),
):
    return list_bid_cases(db, province=province, scaffold_type=scaffold_type)


@router.get("/bids/{case_id}", response_model=ScaffoldBidCaseDetail)
def get_scaffold_bid(case_id: int, db: Session = Depends(get_db)):
    case = get_bid_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="bid case not found")
    return case


@router.get("/prices/reference", response_model=list[ScaffoldPriceReferenceOut])
def get_scaffold_price_references(
    region: str | None = None,
    scaffold_type: str | None = None,
    db: Session = Depends(get_db),
):
    return list_price_references(db, region=region, scaffold_type=scaffold_type)


@router.post("/bids/{case_id}/review")
def post_scaffold_bid_review(case_id: int, payload: ReviewRequest, db: Session = Depends(get_db)):
    task = review_case(db, case_id=case_id, status=payload.status, reviewer_note=payload.reviewer_note)
    if task is None:
        raise HTTPException(status_code=404, detail="bid case not found")
    return {"id": task.id, "case_id": task.case_id, "status": task.status, "reviewer_note": task.reviewer_note}
