from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference


def calculate_reference_for_case(case: ScaffoldBidCase) -> ScaffoldPriceReference | None:
    if case.bid_amount is None:
        return None
    amount = Decimal(case.bid_amount)
    region = case.city or case.province
    if case.pricing_method and "单价" in case.pricing_method and case.area_m2:
        price = (amount / Decimal(case.area_m2)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ScaffoldPriceReference(
            bid_case_id=case.id,
            price_type="direct_or_area_unit",
            scaffold_type=case.scaffold_type,
            region=region,
            calculated_unit="元/㎡",
            calculated_price=price,
            formula="公告给出单价或可按金额/面积核验",
            confidence="high",
            notes="公告存在单价线索，按面积口径入库。",
        )
    if case.area_m2 and Decimal(case.area_m2) > 0:
        price = (amount / Decimal(case.area_m2)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ScaffoldPriceReference(
            bid_case_id=case.id,
            price_type="amount_per_area",
            scaffold_type=case.scaffold_type,
            region=region,
            calculated_unit="元/㎡",
            calculated_price=price,
            formula=f"{amount} / {case.area_m2}",
            confidence="medium",
            notes="按中标金额/面积折算。",
        )
    if case.rental_days and case.rental_days > 0:
        months = Decimal(case.rental_days) / Decimal(30)
        price = (amount / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        confidence = "medium" if case.rental_days >= 90 else "low"
        return ScaffoldPriceReference(
            bid_case_id=case.id,
            price_type="amount_per_month",
            scaffold_type=case.scaffold_type,
            region=region,
            calculated_unit="元/月",
            calculated_price=price,
            formula=f"{amount} / ({case.rental_days} / 30)",
            confidence=confidence,
            notes="缺少工程量，按租期折算金额/月。",
        )
    return None


def replace_reference_for_case(db: Session, case: ScaffoldBidCase) -> ScaffoldPriceReference | None:
    db.query(ScaffoldPriceReference).filter(ScaffoldPriceReference.bid_case_id == case.id).delete()
    reference = calculate_reference_for_case(case)
    if reference is None:
        return None
    db.add(reference)
    db.flush()
    return reference
