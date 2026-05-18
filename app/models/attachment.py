from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BidAttachment(Base):
    __tablename__ = "bid_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    raw_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("bid_raw_documents.id"), nullable=True, index=True
    )
    source_url: Mapped[str] = mapped_column(Text)
    file_url: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(32), index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default="pending", index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    raw_document: Mapped["BidRawDocument | None"] = relationship(
        back_populates="attachments"
    )
