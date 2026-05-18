from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ManagedBrowserRun(Base):
    __tablename__ = "managed_browser_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(128), index=True)
    keyword: Mapped[str] = mapped_column(String(128), index=True)
    mode: Mapped[str] = mapped_column(
        String(32), default="dry-run", server_default="dry-run"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    visited_urls: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    downloaded_files: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    records_created: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    attachments_created: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    blocked_reason: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
