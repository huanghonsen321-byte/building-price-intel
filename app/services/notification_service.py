from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldBidCase
from app.models.notification import NotificationLog
from app.models.price import PriceDaily


@dataclass
class SendResult:
    status: str
    message: str
    error_message: str | None = None


def _contains_any(text: str, values: Iterable[str]) -> bool:
    values = [v for v in values if v]
    if not values:
        return True
    return any(value in text for value in values)


def _record_log(db: Session, event_type: str, channel: str, target: str | None, result: SendResult, retry_count: int = 0) -> NotificationLog:
    log = NotificationLog(
        event_type=event_type,
        channel=channel,
        target=target,
        status=result.status,
        message=result.message,
        error_message=result.error_message,
        retry_count=retry_count,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def send_message(channel: str, target: str | None, message: str, retries: int = 1) -> SendResult:
    if channel == "mock" or not target:
        return SendResult(status="success", message=message)
    if channel != "wecom_webhook":
        return SendResult(status="failed", message=message, error_message=f"unsupported channel: {channel}")

    payload = {"msgtype": "markdown", "markdown": {"content": message}}
    last_error: str | None = None
    for _ in range(max(1, retries + 1)):
        try:
            response = httpx.post(target, json=payload, timeout=8.0)
            response.raise_for_status()
            data = response.json()
            if data.get("errcode", 0) == 0:
                return SendResult(status="success", message=message)
            last_error = str(data)
        except Exception as exc:  # pragma: no cover - network path is covered by mock sender in tests
            last_error = str(exc)
    return SendResult(status="failed", message=message, error_message=last_error)


def build_daily_briefing(db: Session, regions: list[str] | None = None, categories: list[str] | None = None) -> str:
    latest_date = db.scalar(select(PriceDaily.date).order_by(PriceDaily.date.desc()).limit(1)) or date.today()
    stmt = select(PriceDaily).where(PriceDaily.date == latest_date)
    if regions:
        stmt = stmt.where(PriceDaily.region.in_(regions))
    if categories:
        stmt = stmt.where(PriceDaily.category.in_(categories))
    prices = list(db.scalars(stmt.order_by(PriceDaily.category, PriceDaily.region, PriceDaily.product_name)))

    bid_stmt = select(ScaffoldBidCase).order_by(ScaffoldBidCase.publish_date.desc().nullslast(), ScaffoldBidCase.id.desc()).limit(5)
    bids = list(db.scalars(bid_stmt))

    lines = [f"# 每日行情早报 {latest_date.isoformat()}", ""]
    if prices:
        lines.append("## 价格行情")
        for item in prices[:20]:
            change = item.change_value if item.change_value is not None else Decimal("0")
            direction = "↑" if change > 0 else ("↓" if change < 0 else "→")
            city = item.city or ""
            lines.append(f"- {item.category}/{item.region}{city} {item.product_name}: {item.price}{item.unit} {direction}{abs(change)}")
    else:
        lines.append("暂无匹配价格数据。")

    if bids:
        lines.extend(["", "## 重要新公告"])
        for bid in bids:
            amount = f"{(bid.bid_amount / Decimal('10000')).quantize(Decimal('0.01'))}万元" if bid.bid_amount else "金额未披露"
            lines.append(f"- {bid.province or ''}{bid.city or ''} {bid.project_name}：{amount}")
    lines.extend(["", "数据来源：公开价格/公告采集；请以原始 source_url 复核。"])
    return "\n".join(lines)


def send_daily_briefing(
    db: Session,
    channel: str = "mock",
    target: str | None = None,
    regions: list[str] | None = None,
    categories: list[str] | None = None,
) -> SendResult:
    message = build_daily_briefing(db, regions=regions, categories=categories)
    result = send_message(channel=channel, target=target, message=message, retries=1)
    _record_log(db, "daily_briefing", channel, target, result, retry_count=0 if result.status == "success" else 1)
    return result


def alert_for_bid_case(
    db: Session,
    case: ScaffoldBidCase,
    channel: str = "mock",
    target: str | None = None,
    keywords: list[str] | None = None,
    regions: list[str] | None = None,
    min_amount: Decimal | None = None,
) -> SendResult | None:
    text = " ".join(str(part or "") for part in [case.project_name, case.province, case.city, case.buyer, case.winner, case.scaffold_type, case.procurement_type])
    region_text = f"{case.province or ''}{case.city or ''}"
    if keywords and not _contains_any(text, keywords):
        return None
    if regions and not _contains_any(region_text, regions):
        return None
    if min_amount is not None and (case.bid_amount is None or case.bid_amount < min_amount):
        return None
    amount = f"{(case.bid_amount / Decimal('10000')).quantize(Decimal('0.01'))}万元" if case.bid_amount else "金额未披露"
    message = "\n".join(
        [
            "# 重要公告提醒",
            f"项目：{case.project_name}",
            f"地区：{region_text or '-'}",
            f"采购人：{case.buyer or '-'}",
            f"中标人：{case.winner or '-'}",
            f"金额：{amount}",
            f"来源：{case.source_url}",
        ]
    )
    result = send_message(channel=channel, target=target, message=message, retries=1)
    _record_log(db, "bid_alert", channel, target, result, retry_count=0 if result.status == "success" else 1)
    return result
