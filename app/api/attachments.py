from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.attachment import BidAttachment
from app.schemas.attachment import BidAttachmentOut
from app.schemas.pagination import Page
from app.services.attachment_extractor import process_pending_attachments

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


@router.get("", response_model=Page[BidAttachmentOut])
def list_attachments(
    parse_status: str | None = None,
    file_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(BidAttachment)
    if parse_status:
        stmt = stmt.where(BidAttachment.parse_status == parse_status)
    if file_type:
        stmt = stmt.where(BidAttachment.file_type == file_type)

    from sqlalchemy import func
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            stmt.order_by(BidAttachment.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{attachment_id}", response_model=BidAttachmentOut)
def get_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = db.get(BidAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="attachment not found")
    return attachment


@router.post("/parse-pending")
def parse_pending_attachments(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    processed = process_pending_attachments(db, limit=limit)
    db.commit()
    return {"processed": processed, "message": f"Processed {processed} attachments"}
