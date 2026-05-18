
import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import ScaffoldBidCase, ScaffoldPriceReference
from app.models.crawl import BidRawDocument, CrawlSource
from app.models.price import PriceDaily
from app.services.bid_service import create_or_update_case_from_extraction

CRAWLER_LOG_DIR = Path(__file__).resolve().parent / "logs"
CRAWLER_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("building_price_intel.crawlers")
if not logger.handlers:
    handler = logging.FileHandler(CRAWLER_LOG_DIR / "crawler.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

RecordKind = Literal["price", "bid", "reference"]


@dataclass(frozen=True)
class StandardCrawlerRecord:
    record_type: RecordKind
    source_name: str
    source_url: str
    crawl_time: datetime
    publish_time: datetime | date | None = None
    category: str | None = None
    type: str | None = None
    region: str | None = None
    city: str | None = None
    product_name: str | None = None
    specification: str | None = None
    unit: str | None = None
    price: Decimal | None = None
    amount: Decimal | None = None
    title: str | None = None
    text_content: str | None = None
    html_content: str | None = None
    extra: dict[str, Any] | None = None

    @property
    def content_hash(self) -> str:
        payload = json.dumps(_json_safe(asdict(self)), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_standard_record(db: Session, record: StandardCrawlerRecord) -> bool:
    """Write one standardized crawler record into backend tables.

    Returns True when a new DB row was created, False when an existing row was
    updated/deduplicated. This function is shared by Scrapy/Crawlee/pyspider
    adapters so database output stays consistent.
    """
    _ensure_public_record(record)
    try:
        if record.record_type == "price":
            created = _write_price(db, record)
        elif record.record_type == "bid":
            created = _write_bid(db, record)
        elif record.record_type == "reference":
            created = _write_reference(db, record)
        else:
            raise ValueError(f"unsupported record_type={record.record_type}")
        db.commit()
        logger.info("crawler_record_saved", extra={"crawler_source_name": record.source_name, "crawler_source_url": record.source_url, "crawler_record_type": record.record_type, "crawler_created": created})
        return created
    except Exception:
        db.rollback()
        logger.exception("crawler_record_failed", extra={"crawler_source_name": record.source_name, "crawler_source_url": record.source_url, "crawler_record_type": record.record_type})
        raise


def write_standard_records(db: Session, records: list[StandardCrawlerRecord]) -> tuple[int, int]:
    created = 0
    failed = 0
    for record in records:
        try:
            created += int(write_standard_record(db, record))
        except Exception:
            failed += 1
    return created, failed


def _ensure_source(db: Session, record: StandardCrawlerRecord) -> CrawlSource:
    source = db.scalar(select(CrawlSource).where(CrawlSource.name == record.source_name))
    source_type = f"standard_{record.record_type}"
    if source is None:
        source = CrawlSource(name=record.source_name, base_url=_base_url(record.source_url), source_type=source_type, enabled=True)
        db.add(source)
        db.flush()
    else:
        source.source_type = source.source_type or source_type
    return source


def _write_price(db: Session, record: StandardCrawlerRecord) -> bool:
    if not all([record.category, record.region, record.product_name, record.unit, record.price]):
        raise ValueError("price record requires category/region/product_name/unit/price")
    price_date = _as_date(record.publish_time) or _as_date(record.crawl_time) or date.today()
    existing = db.scalar(
        select(PriceDaily).where(
            PriceDaily.date == price_date,
            PriceDaily.category == record.category,
            PriceDaily.region == record.region,
            PriceDaily.city == record.city,
            PriceDaily.product_name == record.product_name,
            PriceDaily.spec == record.specification,
            PriceDaily.source_name == record.source_name,
        )
    )
    if existing is None:
        db.add(
            PriceDaily(
                date=price_date,
                category=record.category,
                region=record.region or "全国",
                city=record.city,
                product_name=record.product_name,
                spec=record.specification,
                material=(record.extra or {}).get("material"),
                unit=record.unit,
                price=record.price,
                change_value=(record.extra or {}).get("change_value"),
                tax_included=(record.extra or {}).get("tax_included", True),
                source_name=record.source_name,
                source_url=record.source_url,
            )
        )
        db.flush()
        _ensure_source(db, record)
        return True
    existing.price = record.price
    existing.unit = record.unit
    existing.source_url = record.source_url
    existing.updated_at = datetime.now(UTC)
    _ensure_source(db, record)
    return False


def _write_bid(db: Session, record: StandardCrawlerRecord) -> bool:
    if not record.title or not record.text_content:
        raise ValueError("bid record requires title and text_content")
    existing = db.scalar(select(BidRawDocument).where(BidRawDocument.source_url == record.source_url))
    created = existing is None
    publish_date = _as_date(record.publish_time)
    if existing is None:
        existing = BidRawDocument(
            source_name=record.source_name,
            source_url=record.source_url,
            title=record.title,
            publish_date=publish_date,
            region=record.region,
            html_content=record.html_content,
            text_content=record.text_content,
            content_hash=record.content_hash,
            crawl_status="saved",
        )
        db.add(existing)
        db.flush()
    else:
        existing.title = record.title
        existing.publish_date = publish_date
        existing.region = record.region
        existing.html_content = record.html_content
        existing.text_content = record.text_content
        existing.content_hash = record.content_hash
    extraction = _bid_extraction_from_standard(record, publish_date)
    create_or_update_case_from_extraction(db, extraction, source_url=record.source_url, raw_document_id=existing.id)
    _ensure_source(db, record)
    return created


def _write_reference(db: Session, record: StandardCrawlerRecord) -> bool:
    case = db.scalar(select(ScaffoldBidCase).where(ScaffoldBidCase.source_url == record.source_url))
    if case is None:
        raise ValueError("reference record requires an existing ScaffoldBidCase with matching source_url")
    existing = db.scalar(select(ScaffoldPriceReference).where(ScaffoldPriceReference.bid_case_id == case.id, ScaffoldPriceReference.calculated_unit == record.unit, ScaffoldPriceReference.price_type == (record.type or "crawler_reference")))
    if existing is None:
        db.add(ScaffoldPriceReference(bid_case_id=case.id, price_type=record.type or "crawler_reference", scaffold_type=record.product_name, region=record.region or record.city, calculated_unit=record.unit or "元/㎡", calculated_price=record.price or Decimal("0"), formula=(record.extra or {}).get("formula", "crawler standard output"), confidence=(record.extra or {}).get("confidence", "medium"), notes=(record.extra or {}).get("notes")))
        db.flush()
        _ensure_source(db, record)
        return True
    existing.calculated_price = record.price or existing.calculated_price
    existing.formula = (record.extra or {}).get("formula", existing.formula)
    _ensure_source(db, record)
    return False


def _bid_extraction_from_standard(record: StandardCrawlerRecord, publish_date: date | None) -> dict[str, Any]:
    extra = record.extra or {}
    return {
        "is_scaffold_related": True,
        "announcement_type": record.type or extra.get("announcement_type") or "中标公告",
        "project_name": record.title,
        "province": record.region,
        "city": record.city,
        "district": extra.get("district"),
        "buyer": extra.get("buyer"),
        "agency": extra.get("agency"),
        "winner": extra.get("winner"),
        "bid_amount": record.amount,
        "publish_date": publish_date.isoformat() if publish_date else None,
        "scaffold_type": record.product_name or extra.get("scaffold_type") or "脚手架",
        "procurement_type": extra.get("procurement_type") or "租赁",
        "service_scope": extra.get("service_scope"),
        "duration_text": extra.get("duration_text"),
        "quantity_text": extra.get("quantity_text"),
        "area_m2": extra.get("area_m2"),
        "tonnage": extra.get("tonnage"),
        "rental_days": extra.get("rental_days"),
        "pricing_method": extra.get("pricing_method") or "总价折算",
        "unit_price_candidates": [],
        "ai_summary": extra.get("ai_summary") or "标准化爬虫记录生成，待 AI/人工复核。",
        "missing_fields": [],
        "confidence": extra.get("confidence", 0.6),
    }


def _ensure_public_record(record: StandardCrawlerRecord) -> None:
    if not record.source_url.startswith(("http://", "https://")):
        raise ValueError("source_url must be public http(s) URL")


def _as_date(value: datetime | date | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value


def _base_url(url: str) -> str:
    parts = url.split("/", 3)
    return "/".join(parts[:3]) if len(parts) >= 3 else url


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
