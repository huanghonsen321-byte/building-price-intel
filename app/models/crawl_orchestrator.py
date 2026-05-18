from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_type: Mapped[str] = mapped_column(String(32), index=True, server_default="daily")
    status: Mapped[str] = mapped_column(String(32), index=True, server_default="running")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    source_filters: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    total_sources: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_keywords: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_saved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_attachments: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_ai_extracted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_review_tasks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notification_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlRunSource(Base):
    __tablename__ = "crawl_run_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    crawl_run_id: Mapped[int] = mapped_column(index=True)
    source_name: Mapped[str] = mapped_column(String(128), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parser_status: Mapped[str] = mapped_column(String(32), server_default="unknown")
    status: Mapped[str] = mapped_column(String(32), index=True, server_default="pending")
    blocked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_saved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
