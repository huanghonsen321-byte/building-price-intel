import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crawlers.base import RawBidDocument
from app.crawlers.mock_public_bid_crawler import MockPublicBidCrawler
from app.crawlers.real_public_sources import (
    BlockedReason,
    BlockedSourceError,
    BusinessSocietyPriceCrawler,
    CentralGovernmentProcurementCrawler,
    ChinaBiddingPublicServiceCrawler,
    ChinaGovernmentProcurementCrawler,
    GuangdongGovernmentProcurementSmartCloudCrawler,
    GuangdongPublicResourceTradingCrawler,
    GuangzhouPublicResourceTradingCrawler,
    NationalPublicResourcePlatformCrawler,
    PublicPriceRow,
)
from app.models.crawl import BidRawDocument, CrawlSource, CrawlTask
from app.models.price import PriceDaily
from app.models.review import ReviewTask
from app.services.attachment_extractor import (
    attachment_text_for_raw_doc,
    discover_and_process_attachments_for_raw_doc,
    enhanced_extract_from_attachment_text,
)
from app.services.bid_service import create_or_update_case_from_extraction



BID_CRAWLER_REGISTRY = {
    "CentralGovernmentProcurementCrawler": CentralGovernmentProcurementCrawler,
    "ChinaBiddingPublicServiceCrawler": ChinaBiddingPublicServiceCrawler,
    "ChinaGovernmentProcurementCrawler": ChinaGovernmentProcurementCrawler,
    "GuangdongPublicResourceTradingCrawler": GuangdongPublicResourceTradingCrawler,
    "GuangdongGovernmentProcurementSmartCloudCrawler": GuangdongGovernmentProcurementSmartCloudCrawler,
    "GuangzhouPublicResourceTradingCrawler": GuangzhouPublicResourceTradingCrawler,
    "NationalPublicResourcePlatformCrawler": NationalPublicResourcePlatformCrawler,
}


FALLBACK_SOURCE_CONFIGS = [
    {
        "name": "全国公共资源交易平台",
        "url": NationalPublicResourcePlatformCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "NationalPublicResourcePlatformCrawler",
        "enabled": True,
        "fallback_kind": "national_public_resource_aggregate",
    },
    {
        "name": "中国政府采购网",
        "url": ChinaGovernmentProcurementCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "ChinaGovernmentProcurementCrawler",
        "enabled": True,
        "fallback_kind": "china_government_procurement",
    },
    {
        "name": "中国招标投标公共服务平台",
        "url": ChinaBiddingPublicServiceCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "ChinaBiddingPublicServiceCrawler",
        "enabled": True,
        "fallback_kind": "national_bidding_public_service",
    },
    {
        "name": "中央政府采购网",
        "url": CentralGovernmentProcurementCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "CentralGovernmentProcurementCrawler",
        "enabled": True,
        "fallback_kind": "central_government_procurement",
    },
]

DEFAULT_BID_SOURCE_CONFIGS = [
    {
        "name": "全国公共资源交易平台",
        "url": NationalPublicResourcePlatformCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "NationalPublicResourcePlatformCrawler",
        "enabled": True,
    },
    {
        "name": "中国政府采购网",
        "url": ChinaGovernmentProcurementCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "ChinaGovernmentProcurementCrawler",
        "enabled": True,
    },
    {
        "name": "中国招标投标公共服务平台",
        "url": ChinaBiddingPublicServiceCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "ChinaBiddingPublicServiceCrawler",
        "enabled": True,
    },
    {
        "name": "中央政府采购网",
        "url": CentralGovernmentProcurementCrawler.base_url,
        "source_type": "real_public_bid",
        "parser_name": "CentralGovernmentProcurementCrawler",
        "enabled": True,
    },
]


def _configured_source_configs_from_env() -> list[dict] | None:
    raw = os.getenv("DAILY_CRAWL_SOURCE_CONFIG_JSON", "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return None


def _enabled_bid_source_configs(source_configs: list[dict] | None, include_default_sources: bool) -> list[dict]:
    configs = list(source_configs) if source_configs is not None else []
    if not configs and include_default_sources:
        configs = list(DEFAULT_BID_SOURCE_CONFIGS)
    return [
        config
        for config in configs
        if config.get("enabled", True) is True
        and (
            config.get("source_type") in {"bid", "real_public_bid"}
            or config.get("type") in {"httpx_html", "planned_public_adapter"}
        )
        and config.get("parser_name")
    ]


def _source_configs_with_fallbacks(config: dict) -> list[dict]:
    fallbacks = [item for item in config.get("fallbacks", []) if isinstance(item, dict)]
    if fallbacks:
        return [fallback for fallback in fallbacks if fallback.get("enabled", True) is True and fallback.get("parser_name")]
    configured_defaults = [fallback for fallback in FALLBACK_SOURCE_CONFIGS if fallback.get("enabled", True) is True]
    # Other compliant fallback categories are operational/manual paths: provincial/city
    # announcement columns, public site search, RSS/open APIs, manual CSV/Excel uploads,
    # and supplier-authorized APIs. They are recorded in source metadata when present;
    # only configured executable fallbacks are run automatically.
    return configured_defaults


def _apply_source_config_metadata(source: CrawlSource, config: dict) -> None:
    source.requires_browser = bool(config.get("requires_browser", source.requires_browser))
    source.requires_manual_review = bool(config.get("requires_manual_review", source.requires_manual_review))
    source.public_page_reachable = bool(config.get("public_page_reachable", source.public_page_reachable))
    source.public_api_found = bool(config.get("public_api_found", source.public_api_found))
    if config.get("parser_status"):
        source.parser_status = str(config["parser_status"])


def _mark_source_success(source: CrawlSource, docs_found: int) -> None:
    source.last_success_at = datetime.now(UTC)
    source.last_blocked_reason = None
    source.parser_status = "ok" if docs_found else BlockedReason.NO_KEYWORD_HITS.value
    source.requires_manual_review = False
    source.reliability_score = min(1.0, float(source.reliability_score or 0.0) + 0.1 + (0.05 if docs_found else 0.0))


def _mark_source_blocked(source: CrawlSource, reason: BlockedReason | str) -> None:
    reason_value = str(reason.value if isinstance(reason, BlockedReason) else reason)
    source.last_blocked_reason = reason_value
    source.parser_status = reason_value
    source.requires_manual_review = True
    source.reliability_score = max(0.0, float(source.reliability_score or 0.0) - 0.2)


def _mark_source_transport_error(source: CrawlSource, message: str) -> None:
    _mark_source_blocked(source, BlockedReason.TRANSPORT_ERROR)
    source.parser_status = BlockedReason.TRANSPORT_ERROR.value


def _ensure_pending_review_task(db: Session, case_id: int, note: str) -> None:
    existing = db.scalar(select(ReviewTask).where(ReviewTask.case_id == case_id, ReviewTask.status == "pending"))
    if existing is None:
        db.add(ReviewTask(case_id=case_id, status="pending", reviewer_note=note))


def _save_bid_docs_with_cases(db: Session, docs: list[RawBidDocument]) -> int:
    saved = 0
    for doc in docs:
        raw, is_new = _save_bid_document(db, doc)
        saved += int(is_new)

        # Discover and process attachments in the raw document HTML
        try:
            discover_and_process_attachments_for_raw_doc(db, raw)
        except Exception:
            pass  # Attachment discovery should never crash the pipeline

        # Collect attachment text for enhanced extraction
        attachment_text = ""
        try:
            attachment_text = attachment_text_for_raw_doc(db, raw.id)
        except Exception:
            pass

        # Use enhanced extraction when attachment text is available
        if attachment_text:
            combined_text = f"{doc.text_content}\n\n--- ATTACHMENT TEXT ---\n{attachment_text}"
            extraction = enhanced_extract_from_attachment_text(
                combined_text, doc.title, doc.publish_date
            )
            # Fall back to simple extraction fields that enhanced may miss
            simple = _simple_extract(doc.text_content, doc.title, doc.publish_date)
            for key in ("project_name", "province", "city", "district", "buyer", "agency", "winner",
                        "scaffold_type", "procurement_type", "service_scope"):
                if not extraction.get(key):
                    extraction[key] = simple.get(key)
        else:
            extraction = _simple_extract(doc.text_content, doc.title, doc.publish_date)

        case = create_or_update_case_from_extraction(
            db, extraction, source_url=doc.source_url, raw_document_id=raw.id
        )
        if case.review_status == "pending" or case.extraction_confidence < Decimal("0.70"):
            _ensure_pending_review_task(
                db,
                case.id,
                f"规则抽取置信度 {case.extraction_confidence}，请复核关键字段。",
            )
    return saved

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
    city = (
        "广州" if "广州" in text else "深圳" if "深圳" in text else "佛山" if "佛山" in text else "东莞" if "东莞" in text else "中山" if "中山" in text else "珠海" if "珠海" in text else "惠州" if "惠州" in text else "江门" if "江门" in text else "肇庆" if "肇庆" in text else "乌兰察布" if "乌兰察布" in text else "呼和浩特" if "呼和浩特" in text else None
    )
    province = "广东" if city in {"广州", "深圳", "佛山", "东莞", "中山", "珠海", "惠州", "江门", "肇庆"} or "广东" in text else "内蒙古" if city in {"乌兰察布", "呼和浩特"} or "内蒙古" in text else None
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


def _run_bid_source_config(
    db: Session,
    config: dict,
    keyword: str,
    bid_html: str | None,
    bid_html_by_parser: dict[str, str] | None,
    errors: list[str],
    *,
    is_fallback: bool = False,
) -> list[RawBidDocument]:
    parser_name = str(config.get("parser_name"))
    crawler_cls = BID_CRAWLER_REGISTRY.get(parser_name)
    if crawler_cls is None:
        errors.append(f"unknown parser_name={parser_name}")
        return []
    crawler = crawler_cls()
    configured_url = config.get("url") or crawler.base_url
    if configured_url:
        crawler.base_url = configured_url
    source = _get_or_create_source(
        db,
        name=config.get("name") or crawler.source_name,
        base_url=configured_url,
        source_type=config.get("source_type") or "bid",
    )
    _apply_source_config_metadata(source, config)
    try:
        if bid_html_by_parser and parser_name in bid_html_by_parser:
            docs = crawler.parse_search_results(bid_html_by_parser[parser_name], keyword=keyword, base_url=config.get("url") or crawler.base_url)
        elif bid_html is not None and parser_name == "ChinaGovernmentProcurementCrawler":
            docs = crawler.parse_search_results(bid_html, keyword=keyword, base_url=config.get("url") or crawler.base_url)
        else:
            docs = crawler.search(keyword)
    except BlockedSourceError as exc:
        _mark_source_blocked(source, exc.reason)
        errors.append(f"{source.name}: {exc.reason.value}")
        return []
    except Exception as exc:
        _mark_source_transport_error(source, str(exc))
        errors.append(f"{source.name}: {BlockedReason.TRANSPORT_ERROR.value}: {exc}")
        return []
    if docs:
        _mark_source_success(source, len(docs))
    else:
        source.parser_status = BlockedReason.NO_KEYWORD_HITS.value if is_fallback else BlockedReason.PARSER_NO_MATCH.value
        source.last_blocked_reason = None
    return docs


def run_mock_crawl(db: Session, keyword: str) -> CrawlTask:
    crawler = MockPublicBidCrawler()
    source = _get_or_create_source(db, name=crawler.source_name, base_url=crawler.base_url, source_type="mock_public_bid")
    task = CrawlTask(source_id=source.id, keyword=keyword, status="running", started_at=datetime.now(UTC))
    db.add(task)
    db.flush()
    try:
        docs = crawler.search(keyword)
        saved = _save_bid_docs_with_cases(db, docs)
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


def run_public_crawl(
    db: Session,
    keyword: str,
    price_html: str | None = None,
    bid_html: str | None = None,
    source_configs: list[dict] | None = None,
    bid_html_by_parser: dict[str, str] | None = None,
    include_default_sources: bool = True,
) -> CrawlTask:
    price_crawler = BusinessSocietyPriceCrawler()
    env_configs = _configured_source_configs_from_env()
    active_source_configs = _enabled_bid_source_configs(source_configs if source_configs is not None else env_configs, include_default_sources)
    price_source = _get_or_create_source(db, name=price_crawler.source_name, base_url=price_crawler.base_url, source_type="real_public_price")
    for config in active_source_configs:
        parser_name = str(config.get("parser_name"))
        crawler_cls = BID_CRAWLER_REGISTRY.get(parser_name)
        if crawler_cls is not None:
            source = _get_or_create_source(db, name=config.get("name") or crawler_cls.source_name, base_url=config.get("url") or crawler_cls.base_url, source_type=config.get("source_type") or "bid")
            _apply_source_config_metadata(source, config)
    task = CrawlTask(source_id=price_source.id, keyword=keyword, status="running", started_at=datetime.now(UTC))
    db.add(task)
    db.flush()
    try:
        if price_html is not None:
            price_rows = price_crawler.parse_prices(price_html, source_url=f"{price_crawler.base_url}/example.html")
        elif active_source_configs or not include_default_sources:
            price_rows = []
        else:
            price_rows = price_crawler.fetch_prices()

        all_docs: list[RawBidDocument] = []
        errors: list[str] = []
        for config in active_source_configs:
            docs = _run_bid_source_config(db, config, keyword, bid_html, bid_html_by_parser, errors)
            all_docs.extend(docs)
            if docs:
                continue
            source_name = config.get("name") or str(config.get("parser_name"))
            source = db.scalar(select(CrawlSource).where(CrawlSource.name == source_name))
            if source is not None and source.last_blocked_reason:
                for fallback_config in _source_configs_with_fallbacks(config):
                    fallback_docs = _run_bid_source_config(db, fallback_config, keyword, bid_html, bid_html_by_parser, errors, is_fallback=True)
                    all_docs.extend(fallback_docs)
                    if fallback_docs:
                        break
            delay = float(os.getenv("DAILY_CRAWL_REQUEST_DELAY_SECONDS", "0") or 0)
            if delay > 0:
                time.sleep(delay)

        saved = 0
        for row in price_rows:
            saved += int(_save_price_row(db, row))
        saved += _save_bid_docs_with_cases(db, all_docs)
        task.status = "success" if all_docs or price_rows or not errors else "failed"
        task.total_found = len(price_rows) + len(all_docs)
        task.total_saved = saved
        if errors:
            task.error_message = "; ".join(errors)[:2000]
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


def build_crawl_dashboard_summary(db: Session) -> dict:
    today = datetime.now(UTC).date()
    sources = list(db.scalars(select(CrawlSource)).all())
    blocked_sources = [source for source in sources if source.last_blocked_reason]
    available_sources = [source for source in sources if source.enabled and not source.last_blocked_reason and source.parser_status in {"ok", BlockedReason.NO_KEYWORD_HITS.value, "unknown"}]
    reason_distribution: dict[str, int] = {}
    for source in blocked_sources:
        reason = source.last_blocked_reason or "unknown"
        reason_distribution[reason] = reason_distribution.get(reason, 0) + 1

    today_successful_source_ids = set(
        db.scalars(
            select(CrawlTask.source_id).where(
                CrawlTask.status == "success",
                CrawlTask.source_id.is_not(None),
                func.date(CrawlTask.finished_at) == today.isoformat(),
            )
        ).all()
    )

    tasks = list(db.scalars(select(CrawlTask).where(CrawlTask.source_id.is_not(None))).all())
    source_by_id = {source.id: source for source in sources}

    def _is_guangdong_source(source: CrawlSource | None) -> bool:
        if source is None:
            return False
        text = f"{source.name} {source.base_url}"
        return any(marker in text for marker in ("广东", "广州", "深圳", "佛山", "东莞", "gd", "gz"))

    def _success_rate(regional: bool | None) -> float:
        scoped: list[CrawlTask] = []
        for task in tasks:
            source = source_by_id.get(task.source_id or -1)
            is_gd = _is_guangdong_source(source)
            if regional is True and not is_gd:
                continue
            if regional is False and is_gd:
                continue
            scoped.append(task)
        if not scoped:
            return 0.0
        return round(sum(1 for task in scoped if task.status == "success") / len(scoped), 4)

    return {
        "blocked_source_count": len(blocked_sources),
        "blocked_reason_distribution": reason_distribution,
        "available_source_count": len(available_sources),
        "today_successful_source_count": len(today_successful_source_ids),
        "guangdong_success_rate": _success_rate(True),
        "national_success_rate": _success_rate(False),
        "source_library_stats": _source_library_stats(),
    }


def _source_library_stats() -> dict:
    """Include source library registry stats in the dashboard."""
    try:
        from app.source_library.registry import get_stats
        stats = get_stats()
        return {
            "total_sources": stats.total_sources,
            "enabled_sources": stats.enabled_sources,
            "parser_ready_sources": stats.parser_ready_sources,
            "blocked_sources": stats.blocked_sources,
            "national_sources": stats.national_sources,
            "guangdong_sources": stats.guangdong_sources,
            "province_source_count": stats.province_source_count,
            "city_source_count": stats.city_source_count,
            "price_source_count": stats.price_source_count,
            "attachment_source_count": stats.attachment_source_count,
            "manual_import_sources": stats.manual_import_sources,
            "authorized_api_sources": stats.authorized_api_sources,
            "by_parser_status": stats.by_parser_status,
        }
    except Exception:
        return {}
