import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base import RawBidDocument
from app.crawlers.mock_public_bid_crawler import MockPublicBidCrawler
from app.crawlers.real_public_sources import BusinessSocietyPriceCrawler, ChinaGovernmentProcurementCrawler, PublicPriceRow
from app.models.crawl import BidRawDocument, CrawlSource, CrawlTask
from app.models.price import PriceDaily
from app.services.bid_service import create_or_update_case_from_extraction


def _amount_to_decimal(value: str | None, unit: str | None) -> Decimal | None:
    if not value:
        return None
    amount = Decimal(value.replace(",", "").replace("，", ""))
    if unit == "亿元":
        amount *= Decimal("100000000")
    elif unit == "万元":
        amount *= Decimal("10000")
    return amount.quantize(Decimal("0.01"))


def _simple_extract(text: str, title: str, publish_date) -> dict:
    amount_match = re.search(r"(?:中标金额|成交金额|合同金额|投标报价)[：:]?\s*(?:人民币)?\s*([0-9.,，]+)\s*(亿元|万元|元)?", text)
    area_match = re.search(r"(?:工程量[：:]?\s*)?(?:脚手架)?(?:工程面积|建筑面积|面积)约?\s*([0-9.,，]+)\s*(?:平方米|㎡|m2)", text)
    days_match = re.search(r"(?:服务期|租期|工期)[：:]?\s*(?:约)?\s*(?:为)?\s*([0-9]+)\s*天|(?:服务期|租期|工期)[：:]?\s*(?:约)?\s*(?:为)?\s*([0-9]+)\s*个月", text)
    months = None
    if days_match and days_match.group(2):
        months = int(days_match.group(2))
    days = int(days_match.group(1)) if days_match and days_match.group(1) else (months * 30 if months else None)
    scaffold_type = "盘扣" if "盘扣" in text else "扣件式钢管脚手架" if "钢管" in text or "扣件式" in text else "脚手架"
    city = "深圳" if "深圳" in text else "乌兰察布" if "乌兰察布" in text else "呼和浩特" if "呼和浩特" in text else None
    province = "广东" if city == "深圳" or "广东" in text else "内蒙古" if city in {"乌兰察布", "呼和浩特"} or "内蒙古" in text else None
    return {
        "is_scaffold_related": True,
        "announcement_type": "中标公告" if "中标" in title else "成交公告",
        "project_name": title.replace("中标公告", "").replace("成交结果公告", ""),
        "province": province,
        "city": city,
        "district": None,
        "buyer": _between(text, "采购人：", "。"),
        "agency": _between(text, "代理机构：", "。"),
        "winner": _between(text, "中标人：", "。") or _between(text, "成交单位：", "。"),
        "bid_amount": _amount_to_decimal(amount_match.group(1), amount_match.group(2) or "元") if amount_match else None,
        "publish_date": publish_date.isoformat() if publish_date else None,
        "scaffold_type": scaffold_type,
        "procurement_type": "租赁" if "租赁" in text else "专业分包",
        "service_scope": _between(text, "服务范围：", "。") or _between(text, "服务内容：", "。"),
        "duration_text": days_match.group(0) if days_match else None,
        "quantity_text": area_match.group(0) if area_match else None,
        "area_m2": Decimal(area_match.group(1).replace(",", "").replace("，", "")) if area_match else None,
        "tonnage": None,
        "rental_days": days,
        "pricing_method": "总价折算",
        "unit_price_candidates": [],
        "ai_summary": "公开公告基于规则抽取生成，待 AI/人工复核。",
        "missing_fields": [],
        "confidence": 0.65 if amount_match else 0.3,
    }


def _between(text: str, start: str, end: str) -> str | None:
    if start not in text:
        return None
    value = text.split(start, 1)[1].split(end, 1)[0].strip()
    return value or None


def _get_or_create_source(db: Session, *, name: str, base_url: str, source_type: str) -> CrawlSource:
    source = db.scalar(select(CrawlSource).where(CrawlSource.name == name))
    if source is None:
        source = CrawlSource(name=name, base_url=base_url, source_type=source_type, enabled=True)
        db.add(source)
        db.flush()
    else:
        source.base_url = base_url
        source.source_type = source_type
    return source


def _save_bid_document(db: Session, doc: RawBidDocument) -> tuple[BidRawDocument, bool]:
    content_hash = hashlib.sha256(f"{doc.source_url}\n{doc.text_content}".encode("utf-8")).hexdigest()
    raw = db.scalar(select(BidRawDocument).where(BidRawDocument.source_url == doc.source_url))
    if raw is None:
        raw = BidRawDocument(
            source_name=doc.source_name,
            source_url=doc.source_url,
            title=doc.title,
            publish_date=doc.publish_date,
            region=doc.region,
            html_content=doc.html_content,
            text_content=doc.text_content,
            content_hash=content_hash,
            crawl_status="saved",
        )
        db.add(raw)
        db.flush()
        return raw, True
    raw.title = doc.title
    raw.publish_date = doc.publish_date
    raw.region = doc.region
    raw.html_content = doc.html_content
    raw.text_content = doc.text_content
    raw.content_hash = content_hash
    return raw, False


def _save_price_row(db: Session, row: PublicPriceRow) -> bool:
    existing = db.scalar(
        select(PriceDaily).where(
            PriceDaily.date == row.date,
            PriceDaily.category == row.category,
            PriceDaily.region == row.region,
            PriceDaily.city == row.city,
            PriceDaily.product_name == row.product_name,
            PriceDaily.spec == row.spec,
            PriceDaily.source_name == row.source_name,
        )
    )
    if existing is None:
        db.add(
            PriceDaily(
                date=row.date,
                category=row.category,
                region=row.region,
                city=row.city,
                product_name=row.product_name,
                spec=row.spec,
                material=row.material,
                unit=row.unit,
                price=row.price,
                change_value=row.change_value,
                tax_included=row.tax_included,
                source_name=row.source_name,
                source_url=row.source_url,
            )
        )
        db.flush()
        return True
    existing.material = row.material
    existing.unit = row.unit
    existing.price = row.price
    existing.change_value = row.change_value
    existing.tax_included = row.tax_included
    existing.source_url = row.source_url
    return False


def run_mock_crawl(db: Session, keyword: str) -> CrawlTask:
    crawler = MockPublicBidCrawler()
    source = _get_or_create_source(db, name=crawler.source_name, base_url=crawler.base_url, source_type="mock_public_bid")
    task = CrawlTask(source_id=source.id, keyword=keyword, status="running", started_at=datetime.now(UTC))
    db.add(task)
    db.flush()
    try:
        docs = crawler.search(keyword)
        saved = 0
        for doc in docs:
            raw, is_new = _save_bid_document(db, doc)
            saved += int(is_new)
            extraction = _simple_extract(doc.text_content, doc.title, doc.publish_date)
            create_or_update_case_from_extraction(db, extraction, source_url=doc.source_url, raw_document_id=raw.id)
        task.status = "success"
        task.total_found = len(docs)
        task.total_saved = saved
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
    finally:
        task.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
    return task


def run_public_crawl(db: Session, keyword: str, price_html: str | None = None, bid_html: str | None = None) -> CrawlTask:
    price_crawler = BusinessSocietyPriceCrawler()
    bid_crawler = ChinaGovernmentProcurementCrawler()
    price_source = _get_or_create_source(db, name=price_crawler.source_name, base_url=price_crawler.base_url, source_type="real_public_price")
    _get_or_create_source(db, name=bid_crawler.source_name, base_url=bid_crawler.base_url, source_type="real_public_bid")
    task = CrawlTask(source_id=price_source.id, keyword=keyword, status="running", started_at=datetime.now(UTC))
    db.add(task)
    db.flush()
    try:
        if price_html is not None:
            price_rows = price_crawler.parse_prices(price_html, source_url=f"{price_crawler.base_url}/example.html")
        else:
            price_rows = price_crawler.fetch_prices()
        if bid_html is not None:
            docs = bid_crawler.parse_search_results(bid_html, keyword=keyword, base_url=bid_crawler.base_url)
        else:
            docs = bid_crawler.search(keyword)

        saved = 0
        for row in price_rows:
            saved += int(_save_price_row(db, row))
        for doc in docs:
            raw, is_new = _save_bid_document(db, doc)
            saved += int(is_new)
            extraction = _simple_extract(doc.text_content, doc.title, doc.publish_date)
            create_or_update_case_from_extraction(db, extraction, source_url=doc.source_url, raw_document_id=raw.id)
        task.status = "success"
        task.total_found = len(price_rows) + len(docs)
        task.total_saved = saved
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
    finally:
        task.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(task)
    return task


def list_crawl_tasks(db: Session) -> list[CrawlTask]:
    return list(db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(100)))
