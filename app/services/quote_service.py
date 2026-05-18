from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldPriceReference
from app.schemas.quote import ScaffoldQuoteRequest, ScaffoldQuoteResponse


def calculate_scaffold_quote(db: Session, payload: ScaffoldQuoteRequest) -> ScaffoldQuoteResponse:
    stmt = select(ScaffoldPriceReference).where(ScaffoldPriceReference.scaffold_type == payload.scaffold_type)
    if payload.region:
        stmt = stmt.where(ScaffoldPriceReference.region == payload.region)
    refs = list(db.scalars(stmt.order_by(ScaffoldPriceReference.created_at.desc()).limit(20)))
    if not refs:
        stmt = select(ScaffoldPriceReference).order_by(ScaffoldPriceReference.created_at.desc()).limit(20)
        refs = list(db.scalars(stmt))
    if not refs:
        return ScaffoldQuoteResponse(
            scaffold_type=payload.scaffold_type,
            region=payload.region,
            calculated_unit="元/㎡",
            reference_price=Decimal("0"),
            estimated_amount=None,
            confidence="low",
            formula="无可用参考价",
            reference_count=0,
        )

    avg_price = (sum((Decimal(item.calculated_price) for item in refs), Decimal("0")) / Decimal(len(refs))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    unit = refs[0].calculated_unit
    estimated = None
    formula = f"参考均价 {avg_price} {unit}"
    if unit == "元/㎡" and payload.area_m2:
        estimated = (avg_price * payload.area_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formula = f"{avg_price} * {payload.area_m2}"
    elif unit == "元/月" and payload.rental_months:
        estimated = (avg_price * payload.rental_months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formula = f"{avg_price} * {payload.rental_months}"

    confidence = "medium" if len(refs) >= 2 else refs[0].confidence
    return ScaffoldQuoteResponse(
        scaffold_type=payload.scaffold_type,
        region=payload.region,
        calculated_unit=unit,
        reference_price=avg_price,
        estimated_amount=estimated,
        confidence=confidence,
        formula=formula,
        reference_count=len(refs),
    )
