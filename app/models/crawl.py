from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, func
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
    attachments: Mapped[list["BidAttachment"]] = relationship(back_populates="raw_document", cascade="all, delete-orphan")
