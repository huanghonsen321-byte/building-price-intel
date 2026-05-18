from decimal import Decimal

from pydantic import BaseModel, Field


class ScaffoldQuoteRequest(BaseModel):
    scaffold_type: str = "盘扣"
    region: str | None = None
    area_m2: Decimal | None = Field(default=None, gt=0)
    rental_days: Decimal | None = Field(default=None, gt=0)
    rental_months: Decimal | None = Field(default=None, gt=0)
    tonnage: Decimal | None = Field(default=None, gt=0)


class ScaffoldQuoteResponse(BaseModel):
    scaffold_type: str
    region: str | None = None
    calculated_unit: str
    reference_price: Decimal
    estimated_amount: Decimal | None = None
    confidence: str
    formula: str
    reference_count: int
