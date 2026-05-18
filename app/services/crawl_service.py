import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.mock_public_bid_crawler import MockPublicBidCrawler
from app.models.crawl import BidRawDocument, CrawlSource, CrawlTask
from app.services.bid_service import create_or_update_case_from_extraction


def _simple_extract(text: str, title: str, publish_date) -> dict:
    amount_match = re.search(r"(?:中标金额|成交金额)：?([0-9.]+)元", text)
    area_match = re.search(r"(?:面积|脚手架面积)([0-9.]+)平方米", text)
    days_match = re.search(r"(?:服务期：?([0-9]+)天|租期：?([0-9]+)个月)", text)
    months = None
    if days_match and days_match.group(2):
        months = int(days_match.group(2))
    days = int(days_match.group(1)) if days_match and days_match.group(1) else (months * 30 if months else None)
    scaffold_type = "盘扣" if "盘扣" in text else "扣件式钢管脚手架" if "钢管" in text or "扣件式" in text else "脚手架"
    city = "乌兰察布" if "乌兰察布" in text else "呼和浩特" if "呼和浩特" in text else None
    return {
        "is_scaffold_related": True,
        "announcement_type": "中标公告" if "中标" in title else "成交公告",
        "project_name": title.replace("中标公告", "").replace("成交结果公告", ""),
        "province": "内蒙古",
        "city": city,
        "district": None,
        "buyer": _between(text, "采购人：", "。"),
        "agency": _between(text, "代理机构：", "。"),
        "winner": _between(text, "中标人：", "。") or _between(text, "成交单位：", "。"),
        "bid_amount": Decimal(amount_match.group(1)) if amount_match else None,
        "publish_date": publish_date.isoformat() if publish_date else None,
        "scaffold_type": scaffold_type,
        "procurement_type": "租赁" if "租赁" in text else "专业分包",
        "service_scope": _between(text, "服务范围：", "。") or _between(text, "服务内容：", "。"),
        "duration_text": days_match.group(0) if days_match else None,
        "quantity_text": area_match.group(0) if area_match else None,
        "area_m2": Decimal(area_match.group(1)) if area_match else None,
        "tonnage": None,
        "rental_days": days,
        "pricing_method": "总价折算",
        "unit_price_candidates": [],
        "ai_summary": "mock 爬虫基于规则抽取生成。",
        "missing_fields": [],
        "confidence": 0.65 if amount_match else 0.3,
    }


def _between(text: str, start: str, end: str) -> str | None:
    if start not in text:
        return None
    value = text.split(start, 1)[1].split(end, 1)[0].strip()
    return value or None


def run_mock_crawl(db: Session, keyword: str) -> CrawlTask:
    crawler = MockPublicBidCrawler()
    source = db.scalar(select(CrawlSource).where(CrawlSource.name == crawler.source_name))
    if source is None:
        source = CrawlSource(name=crawler.source_name, base_url=crawler.base_url, source_type="mock_public_bid", enabled=True)
        db.add(source)
        db.flush()

    task = CrawlTask(source_id=source.id, keyword=keyword, status="running", started_at=datetime.now(UTC))
    db.add(task)
    db.flush()
    try:
        docs = crawler.search(keyword)
        saved = 0
        for doc in docs:
            content_hash = hashlib.sha256(doc.text_content.encode("utf-8")).hexdigest()
            raw = db.scalar(select(BidRawDocument).where(BidRawDocument.content_hash == content_hash))
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
                saved += 1
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


def list_crawl_tasks(db: Session) -> list[CrawlTask]:
    return list(db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(100)))
