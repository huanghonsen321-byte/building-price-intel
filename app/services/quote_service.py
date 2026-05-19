from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldPriceReference
from app.schemas.quote import ScaffoldQuoteCostBreakdown, ScaffoldQuoteRequest, ScaffoldQuoteResponse


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _zero_breakdown() -> ScaffoldQuoteCostBreakdown:
    return ScaffoldQuoteCostBreakdown()


def _normalize_method(payload: ScaffoldQuoteRequest, unit: str | None) -> str:
    if payload.pricing_method:
        return payload.pricing_method
    if payload.fixed_total_price:
        return "总价折算"
    if payload.tonnage and payload.rental_days:
        return "元/吨/天"
    if payload.area_m2:
        return "元/㎡"
    if payload.rental_months:
        return "元/月"
    if unit == "元/吨/天":
        return "元/吨/天"
    if unit == "元/月":
        return "元/月"
    return "元/㎡"


def _apply_costs(base_fee: Decimal, payload: ScaffoldQuoteRequest) -> ScaffoldQuoteCostBreakdown:
    setup = _money(payload.setup_dismantle_fee)
    transport = _money(payload.transport_fee)
    loss_fee = _money(base_fee * payload.loss_rate)
    subtotal = _money(base_fee + setup + transport + loss_fee)
    tax_fee = _money(subtotal * payload.tax_rate)
    profit_fee = _money((subtotal + tax_fee) * payload.profit_rate)
    total = _money(subtotal + tax_fee + profit_fee)
    return ScaffoldQuoteCostBreakdown(
        base_rental_fee=_money(base_fee),
        setup_dismantle_fee=setup,
        transport_fee=transport,
        loss_fee=loss_fee,
        subtotal_before_tax_profit=subtotal,
        tax_fee=tax_fee,
        profit_fee=profit_fee,
        total_amount=total,
    )


def _response_without_refs(payload: ScaffoldQuoteRequest) -> ScaffoldQuoteResponse:
    return ScaffoldQuoteResponse(
        scaffold_type=payload.scaffold_type,
        region=payload.region,
        pricing_method=payload.pricing_method or "元/㎡",
        calculated_unit="元/㎡",
        reference_price=Decimal("0"),
        estimated_amount=None,
        unit_area_price=None,
        unit_ton_day_price=None,
        cost_breakdown=_zero_breakdown(),
        confidence="low",
        formula="无可用参考价",
        reference_count=0,
    )


def calculate_scaffold_quote(db: Session, payload: ScaffoldQuoteRequest) -> ScaffoldQuoteResponse:
    stmt = select(ScaffoldPriceReference).where(ScaffoldPriceReference.scaffold_type == payload.scaffold_type)
    if payload.region:
        stmt = stmt.where(ScaffoldPriceReference.region == payload.region)
    refs = list(db.scalars(stmt.order_by(ScaffoldPriceReference.created_at.desc()).limit(20)))
    if not refs:
        stmt = select(ScaffoldPriceReference).order_by(ScaffoldPriceReference.created_at.desc()).limit(20)
        refs = list(db.scalars(stmt))
    if not refs:
        return _response_without_refs(payload)

    method = _normalize_method(payload, refs[0].calculated_unit)
    compatible_refs = [ref for ref in refs if ref.calculated_unit == method]
    if compatible_refs:
        refs = compatible_refs
    avg_price = _money(sum((Decimal(item.calculated_price) for item in refs), Decimal("0")) / Decimal(len(refs)))
    unit = refs[0].calculated_unit
    if payload.fixed_total_price:
        unit = "总价"
        method = "总价折算"
        avg_price = _money(payload.fixed_total_price)

    estimated: Decimal | None = None
    base_fee = Decimal("0")
    formula = f"参考均价 {avg_price} {unit}，缺少可匹配的报价参数"

    if method == "总价折算":
        estimated = _money(payload.fixed_total_price or avg_price)
        base_fee = estimated
        formula = f"总价 {estimated} 元折算"
    elif unit == "元/㎡":
        if payload.area_m2:
            base_fee = _money(avg_price * payload.area_m2)
            formula = f"材料租赁费：{payload.area_m2}㎡ × {avg_price}元/㎡"
        else:
            formula = "缺少 area_m2，无法按 元/㎡ 估算"
    elif unit == "元/吨/天":
        missing = []
        if not payload.tonnage:
            missing.append("tonnage")
        if not payload.rental_days:
            missing.append("rental_days")
        if not missing:
            base_fee = _money(avg_price * payload.tonnage * payload.rental_days)
            formula = f"材料租赁费：{payload.tonnage}吨 × {payload.rental_days}天 × {avg_price}元/吨/天"
        else:
            formula = f"缺少 {', '.join(missing)}，无法按 元/吨/天 估算"
    elif unit == "元/月":
        if payload.rental_months:
            base_fee = _money(avg_price * payload.rental_months)
            formula = f"材料租赁费：{payload.rental_months}月 × {avg_price}元/月"
        else:
            formula = "缺少 rental_months，无法按 元/月 估算"

    if base_fee > 0:
        breakdown = _apply_costs(base_fee, payload)
        estimated = breakdown.total_amount
        formula = (
            f"{formula}；搭拆费 {breakdown.setup_dismantle_fee} 元；运输费 {breakdown.transport_fee} 元；"
            f"损耗 {payload.loss_rate * 100}%={breakdown.loss_fee} 元；税费 {payload.tax_rate * 100}%={breakdown.tax_fee} 元；"
            f"利润 {payload.profit_rate * 100}%={breakdown.profit_fee} 元；合计 {estimated} 元"
        )
    else:
        breakdown = _zero_breakdown()

    unit_area_price = _money(estimated / payload.area_m2) if estimated is not None and payload.area_m2 else None
    unit_ton_day_price = _money(estimated / payload.tonnage / payload.rental_days) if estimated is not None and payload.tonnage and payload.rental_days else None
    confidence = "medium" if len(refs) >= 2 else refs[0].confidence
    return ScaffoldQuoteResponse(
        scaffold_type=payload.scaffold_type,
        region=payload.region,
        pricing_method=method,
        calculated_unit=unit,
        reference_price=avg_price,
        estimated_amount=estimated,
        unit_area_price=unit_area_price,
        unit_ton_day_price=unit_ton_day_price,
        cost_breakdown=breakdown,
        confidence=confidence,
        formula=formula,
        reference_count=len(refs),
    )
