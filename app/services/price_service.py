from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.price import PriceDaily


def list_today_prices(db: Session) -> list[PriceDaily]:
    latest_date = db.scalar(select(PriceDaily.date).order_by(PriceDaily.date.desc()).limit(1))
    if latest_date is None:
        return []
    return list(db.scalars(select(PriceDaily).where(PriceDaily.date == latest_date).order_by(PriceDaily.category, PriceDaily.product_name)))


def list_prices(
    db: Session,
    category: str | None = None,
    region: str | None = None,
    city: str | None = None,
    product_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PriceDaily], int]:
    stmt = select(PriceDaily)
    if category:
        stmt = stmt.where(PriceDaily.category == category)
    if region:
        stmt = stmt.where(PriceDaily.region == region)
    if city:
        stmt = stmt.where(PriceDaily.city == city)
    if product_name:
        stmt = stmt.where(PriceDaily.product_name.ilike(f"%{product_name}%"))
    if date_from:
        stmt = stmt.where(PriceDaily.date >= date_from)
    if date_to:
        stmt = stmt.where(PriceDaily.date <= date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    items = list(db.scalars(stmt.order_by(PriceDaily.date.desc(), PriceDaily.category, PriceDaily.id.desc()).offset(offset).limit(page_size)))
    return items, total


def list_trends(db: Session, category: str, product_name: str | None = None, days: int = 30) -> list[PriceDaily]:
    since = date.today() - timedelta(days=days)
    stmt = select(PriceDaily).where(PriceDaily.category == category, PriceDaily.date >= since)
    if product_name:
        stmt = stmt.where(PriceDaily.product_name == product_name)
    return list(db.scalars(stmt.order_by(PriceDaily.date.asc())))
