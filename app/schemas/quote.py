from decimal import Decimal

from pydantic import BaseModel, Field


class ScaffoldQuoteRequest(BaseModel):
    scaffold_type: str = "盘扣"
    region: str | None = None
    pricing_method: str | None = None
    area_m2: Decimal | None = Field(default=None, gt=0)
    rental_days: Decimal | None = Field(default=None, gt=0)
    rental_months: Decimal | None = Field(default=None, gt=0)
    tonnage: Decimal | None = Field(default=None, gt=0)
    setup_dismantle_fee: Decimal = Field(default=Decimal("0"), ge=0)
    transport_fee: Decimal = Field(default=Decimal("0"), ge=0)
    loss_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    profit_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    fixed_total_price: Decimal | None = Field(default=None, gt=0)


class ScaffoldQuoteCostBreakdown(BaseModel):
    base_rental_fee: Decimal = Decimal("0")
    setup_dismantle_fee: Decimal = Decimal("0")
    transport_fee: Decimal = Decimal("0")
    loss_fee: Decimal = Decimal("0")
    subtotal_before_tax_profit: Decimal = Decimal("0")
    tax_fee: Decimal = Decimal("0")
    profit_fee: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")


class ScaffoldQuoteResponse(BaseModel):
    scaffold_type: str
    region: str | None = None
    pricing_method: str
    calculated_unit: str
    reference_price: Decimal
    estimated_amount: Decimal | None = None
    unit_area_price: Decimal | None = None
    unit_ton_day_price: Decimal | None = None
    cost_breakdown: ScaffoldQuoteCostBreakdown
    confidence: str
    formula: str
    reference_count: int
