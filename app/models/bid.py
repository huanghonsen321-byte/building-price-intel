from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScaffoldBidCase(Base):
    __tablename__ = "scaffold_bid_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    raw_document_id: Mapped[int | None] = mapped_column(ForeignKey("bid_raw_documents.id"), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(512), index=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buyer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    agency: Mapped[str | None] = mapped_column(String(256), nullable=True)
    winner: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bid_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    announcement_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scaffold_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    procurement_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    quantity_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    area_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tonnage: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    rental_days: Mapped[int | None] = mapped_column(nullable=True)
    pricing_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.0"), server_default="0.0", index=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    raw_document: Mapped["BidRawDocument | None"] = relationship(back_populates="bid_case")
    price_references: Mapped[list["ScaffoldPriceReference"]] = relationship(back_populates="bid_case", cascade="all, delete-orphan")


class ScaffoldPriceReference(Base):
    __tablename__ = "scaffold_price_references"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bid_case_id: Mapped[int] = mapped_column(ForeignKey("scaffold_bid_cases.id"), index=True)
    price_type: Mapped[str] = mapped_column(String(64), index=True)
    scaffold_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    calculated_unit: Mapped[str] = mapped_column(String(32))
    calculated_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    formula: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(32), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bid_case: Mapped[ScaffoldBidCase] = relationship(back_populates="price_references")
