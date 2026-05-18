from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
