from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldPriceReference
from app.schemas.quote import ScaffoldQuoteRequest, ScaffoldQuoteResponse


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _requested_unit(payload: ScaffoldQuoteRequest) -> str | None:
    if payload.area_m2:
        return "元/㎡"
    if payload.tonnage or payload.rental_days:
        return "元/吨/天"
    if payload.rental_months:
        return "元/月"
    return None


def _latest_same_unit(
    refs: list[ScaffoldPriceReference],
) -> list[ScaffoldPriceReference]:
    if not refs:
        return []
    unit = refs[0].calculated_unit
    return [item for item in refs if item.calculated_unit == unit]


def _load_references(
    db: Session, payload: ScaffoldQuoteRequest, requested_unit: str | None
) -> list[ScaffoldPriceReference]:
    def fetch(
        *,
        scaffold_type: str | None = None,
        region: str | None = None,
        unit: str | None = None,
    ) -> list[ScaffoldPriceReference]:
        stmt = select(ScaffoldPriceReference)
        if scaffold_type:
            stmt = stmt.where(ScaffoldPriceReference.scaffold_type == scaffold_type)
        if region:
            stmt = stmt.where(ScaffoldPriceReference.region == region)
        if unit:
            stmt = stmt.where(ScaffoldPriceReference.calculated_unit == unit)
        return list(
            db.scalars(
                stmt.order_by(
                    ScaffoldPriceReference.created_at.desc(),
                    ScaffoldPriceReference.id.desc(),
                ).limit(20)
            )
        )

    attempts: list[dict[str, str | None]] = []
    if payload.region:
        attempts.append(
            {
                "scaffold_type": payload.scaffold_type,
                "region": payload.region,
                "unit": requested_unit,
            }
        )
    attempts.append(
        {"scaffold_type": payload.scaffold_type, "region": None, "unit": requested_unit}
    )
    if requested_unit:
        attempts.append(
            {"scaffold_type": None, "region": payload.region, "unit": requested_unit}
            if payload.region
            else {"scaffold_type": None, "region": None, "unit": requested_unit}
        )
        if payload.region:
            attempts.append(
                {"scaffold_type": None, "region": None, "unit": requested_unit}
            )

    seen: set[tuple[str | None, str | None, str | None]] = set()
    for attempt in attempts:
        key = (attempt["scaffold_type"], attempt["region"], attempt["unit"])
        if key in seen:
            continue
        seen.add(key)
        refs = fetch(**attempt)
        if refs:
            return refs if attempt["unit"] else _latest_same_unit(refs)

    fallback_attempts: list[dict[str, str | None]] = []
    if payload.region:
        fallback_attempts.append(
            {
                "scaffold_type": payload.scaffold_type,
                "region": payload.region,
                "unit": None,
            }
        )
    fallback_attempts.append(
        {"scaffold_type": payload.scaffold_type, "region": None, "unit": None}
    )
    fallback_attempts.append({"scaffold_type": None, "region": None, "unit": None})
    for attempt in fallback_attempts:
        refs = fetch(**attempt)
        same_unit_refs = _latest_same_unit(refs)
        if same_unit_refs:
            return same_unit_refs
    return []


def calculate_scaffold_quote(
    db: Session, payload: ScaffoldQuoteRequest
) -> ScaffoldQuoteResponse:
    refs = _load_references(db, payload, _requested_unit(payload))
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

    avg_price = _money(
        sum((Decimal(item.calculated_price) for item in refs), Decimal("0"))
        / Decimal(len(refs))
    )
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
            formula = (
                f"{payload.tonnage}吨 × {payload.rental_days}天 × {avg_price}元/吨/天"
            )
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
