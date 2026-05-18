from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.price import PriceDailyOut, PriceTrendPoint
from app.services.price_service import list_prices, list_today_prices, list_trends

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/today", response_model=list[PriceDailyOut])
def get_today_prices(db: Session = Depends(get_db)):
    return list_today_prices(db)


@router.get("", response_model=list[PriceDailyOut])
def get_prices(
    category: str | None = None,
    region: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db),
):
    return list_prices(db, category=category, region=region, city=city)


@router.get("/trends", response_model=list[PriceTrendPoint])
def get_price_trends(
    category: str = Query(default="steel"),
    product_name: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return list_trends(db, category=category, product_name=product_name, days=days)
