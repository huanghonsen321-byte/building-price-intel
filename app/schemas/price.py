from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceDailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    category: str
    region: str
    city: str | None = None
    product_name: str
    spec: str | None = None
    material: str | None = None
    unit: str
    price: Decimal
    change_value: Decimal | None = None
    tax_included: bool
    source_name: str
    source_url: str | None = None
    updated_at: datetime
    created_at: datetime


class PriceTrendPoint(BaseModel):
    date: date
    price: Decimal
    product_name: str
    region: str
    city: str | None = None
    unit: str
