from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BidRawDocument(Base):
    __tablename__ = "bid_raw_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(128), index=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    crawl_status: Mapped[str] = mapped_column(String(32), default="saved", server_default="saved", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    bid_case: Mapped["ScaffoldBidCase | None"] = relationship(back_populates="raw_document")


class CrawlSource(Base):
    __tablename__ = "crawl_sources"
    __table_args__ = (UniqueConstraint("name", name="uq_crawl_sources_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    base_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), default="mock_public_bid", server_default="mock_public_bid")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    rate_limit_seconds: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tasks: Mapped[list["CrawlTask"]] = relationship(back_populates="source")


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_sources.id"), nullable=True, index=True)
    keyword: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_saved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[CrawlSource | None] = relationship(back_populates="tasks")
