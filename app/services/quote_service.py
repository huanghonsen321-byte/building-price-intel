from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldPriceReference
from app.schemas.quote import ScaffoldQuoteRequest, ScaffoldQuoteResponse


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    avg_price = _money(sum((Decimal(item.calculated_price) for item in refs), Decimal("0")) / Decimal(len(refs)))
    unit = refs[0].calculated_unit
    estimated = None
    formula = f"参考均价 {avg_price} {unit}，缺少可匹配的报价参数"

    if unit == "元/㎡":
        if payload.area_m2:
            estimated = _money(avg_price * payload.area_m2)
            formula = f"{payload.area_m2}㎡ × {avg_price}元/㎡"
        else:
            formula = "缺少 area_m2，无法按 元/㎡ 估算"
    elif unit == "元/吨/天":
        missing = []
        if not payload.tonnage:
            missing.append("tonnage")
        if not payload.rental_days:
            missing.append("rental_days")
        if not missing:
            estimated = _money(avg_price * payload.tonnage * payload.rental_days)
            formula = f"{payload.tonnage}吨 × {payload.rental_days}天 × {avg_price}元/吨/天"
        else:
            formula = f"缺少 {', '.join(missing)}，无法按 元/吨/天 估算"
    elif unit == "元/月":
        if payload.rental_months:
            estimated = _money(avg_price * payload.rental_months)
            formula = f"{payload.rental_months}月 × {avg_price}元/月"
        else:
            formula = "缺少 rental_months，无法按 元/月 估算"

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
