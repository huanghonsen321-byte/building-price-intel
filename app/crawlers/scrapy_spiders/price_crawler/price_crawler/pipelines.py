
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.crawlers.standard_output import StandardCrawlerRecord, write_standard_record


class DatabasePipeline:
    """Write Scrapy items into backend SQLAlchemy tables."""

    def open_spider(self, spider):
        self.db = SessionLocal()

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        record = StandardCrawlerRecord(
            record_type=item.get("record_type", "price"),
            source_name=item["source_name"],
            source_url=item["source_url"],
            crawl_time=item.get("crawl_time") or datetime.now(UTC),
            publish_time=item.get("publish_time"),
            category=item.get("category"),
            type=item.get("type"),
            region=item.get("region"),
            city=item.get("city"),
            product_name=item.get("product_name"),
            specification=item.get("specification"),
            unit=item.get("unit"),
            price=_decimal_or_none(item.get("price")),
            amount=_decimal_or_none(item.get("amount")),
            title=item.get("title"),
            text_content=item.get("text_content"),
            html_content=item.get("html_content"),
            extra=item.get("extra") or {},
        )
        write_standard_record(self.db, record)
        return item


def _decimal_or_none(value):
    if value is None or value == "":
        return None
    return Decimal(str(value))
