from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceDaily(Base):
    __tablename__ = "price_daily"
    __table_args__ = (
        UniqueConstraint("date", "category", "region", "city", "product_name", "spec", "source_name", name="uq_price_daily_natural"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), index=True)
    spec: Mapped[str | None] = mapped_column(String(128), nullable=True)
    material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str] = mapped_column(String(32))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    change_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tax_included: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    source_name: Mapped[str] = mapped_column(String(128), index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
