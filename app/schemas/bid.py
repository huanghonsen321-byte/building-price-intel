from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScaffoldPriceReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bid_case_id: int
    price_type: str
    scaffold_type: str | None = None
    region: str | None = None
    calculated_unit: str
    calculated_price: Decimal
    formula: str
    confidence: str
    notes: str | None = None
    created_at: datetime


class ScaffoldBidCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_document_id: int | None = None
    project_name: str
    province: str | None = None
    city: str | None = None
    district: str | None = None
    buyer: str | None = None
    agency: str | None = None
    winner: str | None = None
    bid_amount: Decimal | None = None
    announcement_type: str | None = None
    scaffold_type: str | None = None
    procurement_type: str | None = None
    service_scope: str | None = None
    duration_text: str | None = None
    quantity_text: str | None = None
    area_m2: Decimal | None = None
    tonnage: Decimal | None = None
    rental_days: int | None = None
    pricing_method: str | None = None
    source_url: str
    publish_date: date | None = None
    ai_summary: str | None = None
    extraction_confidence: Decimal
    review_status: str
    created_at: datetime
    updated_at: datetime


class ScaffoldBidCaseDetail(ScaffoldBidCaseOut):
    price_references: list[ScaffoldPriceReferenceOut] = []


class ReviewRequest(BaseModel):
    status: Literal["pending", "approved", "rejected"]
    reviewer_note: str | None = None
