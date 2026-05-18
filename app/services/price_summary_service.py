from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price import PriceDaily


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def generate_today_price_summary(db: Session, category: str | None = None) -> dict[str, Any]:
    latest_date = db.scalar(select(PriceDaily.date).order_by(PriceDaily.date.desc()).limit(1))
    if latest_date is None:
        return {
            "date": date.today().isoformat(),
            "total_records": 0,
            "summary_text": "今日行情摘要：暂无价格数据，无法生成行情判断。",
            "regions": {},
            "anomalies": [],
            "updated_at": None,
        }

    stmt = select(PriceDaily).where(PriceDaily.date == latest_date)
    if category:
        stmt = stmt.where(PriceDaily.category == category)
    rows = list(db.scalars(stmt.order_by(PriceDaily.region, PriceDaily.city, PriceDaily.product_name)))

    grouped: dict[str, list[PriceDaily]] = defaultdict(list)
    for row in rows:
        grouped[row.region].append(row)

    regions: dict[str, dict[str, Any]] = {}
    anomalies: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for region, items in grouped.items():
        prices = [_decimal(item.price) for item in items]
        changes = [_decimal(item.change_value) for item in items if item.change_value is not None]
        avg_price = Decimal(str(mean(prices))).quantize(Decimal("0.01")) if prices else Decimal("0.00")
        avg_change = Decimal(str(mean(changes))).quantize(Decimal("0.01")) if changes else Decimal("0.00")
        direction = "上涨" if avg_change > 0 else ("下跌" if avg_change < 0 else "持平")
        regions[region] = {
            "count": len(items),
            "average_price": float(avg_price),
            "average_change": float(avg_change),
            "direction": direction,
            "updated_at": max(str(item.updated_at) for item in items),
        }
        text_parts.append(f"{region}{len(items)}条，均价约{avg_price}元，较前期{direction}{abs(avg_change)}元")
        for item in items:
            change = _decimal(item.change_value)
            if abs(change) >= Decimal("100"):
                anomalies.append(
                    {
                        "region": item.region,
                        "city": item.city,
                        "product_name": item.product_name,
                        "price": float(_decimal(item.price)),
                        "change_value": float(change),
                        "reason": "单日波动达到或超过100元",
                    }
                )

    if rows:
        summary_text = f"今日行情摘要（{latest_date.isoformat()}）：" + "；".join(text_parts) + "。"
        if anomalies:
            summary_text += f"发现{len(anomalies)}条异常波动，建议人工复核来源。"
        else:
            summary_text += "暂未发现明显异常波动。"
    else:
        summary_text = f"今日行情摘要（{latest_date.isoformat()}）：当前筛选条件下暂无价格数据。"

    return {
        "date": latest_date.isoformat(),
        "total_records": len(rows),
        "summary_text": summary_text,
        "regions": regions,
        "anomalies": anomalies,
        "updated_at": max((str(row.updated_at) for row in rows), default=None),
    }
