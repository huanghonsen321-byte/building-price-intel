from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.notification import NotificationLog
from app.services.notification_service import send_daily_briefing

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/daily-briefing/send")
def post_daily_briefing(
    channel: str = Query(default="mock"),
    target: str | None = None,
    region: list[str] | None = Query(default=None),
    category: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
):
    result = send_daily_briefing(db, channel=channel, target=target, regions=region, categories=category)
    return {"status": result.status, "message": result.message, "error_message": result.error_message}


@router.get("/logs")
def get_notification_logs(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(NotificationLog).order_by(NotificationLog.created_at.desc(), NotificationLog.id.desc())
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return {
        "items": [
            {
                "id": item.id,
                "event_type": item.event_type,
                "channel": item.channel,
                "target": item.target,
                "status": item.status,
                "message": item.message,
                "error_message": item.error_message,
                "retry_count": item.retry_count,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "page": page,
        "page_size": page_size,
    }
