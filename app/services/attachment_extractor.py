"""Attachment discovery, download, and text extraction.

Handles PDF (pypdf), DOCX (python-docx), XLSX (openpyxl), and HTML
attachments. Operates with a 20 MB default file size limit. Sanitises
extracted text and stores it in bid_attachments for downstream AI
extraction.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import BidAttachment
from app.models.crawl import BidRawDocument

USER_AGENT = "building-price-intel/0.1 (+public-data; contact: local-development)"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ATTACHMENT_CACHE_DIR = Path(os.getenv("ATTACHMENT_CACHE_DIR", "/tmp/building-price-intel/attachments"))

logger = logging.getLogger("building_price_intel.attachments")

ATTACHMENT_LINK_PATTERNS: list[re.Pattern] = [
    re.compile(r"\.pdf(\?|$)", re.I),
    re.compile(r"\.docx?(\?|$)", re.I),
    re.compile(r"\.xlsx?(\?|$)", re.I),
]

ATTACHMENT_KEYWORDS: list[str] = [
    "附件", "下载", "招标文件", "中标结果", "采购合同",
    "工程量清单", "报价清单", "投标文件",
]

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "docx",
    ".xls": "xls",
    ".xlsx": "xlsx",
    ".htm": "html",
    ".html": "html",
}


def discover_attachment_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Scan HTML for attachment download links.

    Returns list of (file_url, label) tuples where file_url is absolute.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = str(link.get("href", "") or "").strip()
        if not href:
            continue
        label = link.get_text(" ", strip=True)
        combined = f"{href} {label}"

        # Check for attachment file extensions
        is_attachment = any(p.search(href) for p in ATTACHMENT_LINK_PATTERNS)
        # Also check for keyword hints
        has_keyword = any(kw in combined for kw in ATTACHMENT_KEYWORDS) and any(
            ext in href.lower() for ext in SUPPORTED_EXTENSIONS
        )

        if not (is_attachment or has_keyword):
            continue

        absolute_url = urljoin(base_url, href)
        if absolute_url not in seen:
            seen.add(absolute_url)
            found.append((absolute_url, label or href))
    return found


def _classify_file_type(url: str) -> str:
    lower = url.lower().split("?")[0]
    for ext, ftype in SUPPORTED_EXTENSIONS.items():
        if lower.endswith(ext):
            return ftype
    return "unknown"


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name or "attachment"
    if not any(name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        name = f"{name}.unknown"
    return name[:512]


def download_attachment(file_url: str) -> tuple[bytes | None, str | None]:
    """Download attachment bytes. Returns (content, error_message)."""
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True
        ) as client:
            # HEAD first to check size
            head = client.head(file_url)
            content_length = head.headers.get("content-length")
            if content_length and int(content_length) > MAX_FILE_SIZE:
                return None, f"oversize: {content_length} bytes exceeds {MAX_FILE_SIZE} limit"
            response = client.get(file_url)
            response.raise_for_status()
            data = response.content
            if len(data) > MAX_FILE_SIZE:
                return None, f"oversize: {len(data)} bytes exceeds {MAX_FILE_SIZE} limit"
            return data, None
    except Exception as exc:
        return None, f"download failed: {exc}"


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}")


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        parts: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # Also extract table content
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells if cell.text.strip())
                if row_text.strip():
                    parts.append(row_text)
        return "\n".join(parts)
    except Exception as exc:
        raise RuntimeError(f"DOCX extraction failed: {exc}")


def _extract_xlsx(data: bytes) -> str:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"[Sheet: {sheet_name}]")
            for row in ws.iter_rows(values_only=True):
                values = [str(v) for v in row if v is not None]
                if values:
                    parts.append(" | ".join(values))
            if len(parts) > 5000:
                parts.append("[truncated: too many rows]")
                break
        wb.close()
        return "\n".join(parts)
    except Exception as exc:
        raise RuntimeError(f"XLSX extraction failed: {exc}")


def _extract_html(data: bytes) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(data, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)
    except Exception as exc:
        raise RuntimeError(f"HTML extraction failed: {exc}")


EXTRACTORS: dict[str, callable] = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "doc": _extract_docx,
    "xlsx": _extract_xlsx,
    "xls": _extract_xlsx,
    "html": _extract_html,
    "htm": _extract_html,
}


def extract_text(data: bytes, file_type: str) -> str:
    extractor = EXTRACTORS.get(file_type)
    if extractor is None:
        raise ValueError(f"Unsupported file type: {file_type}")
    return extractor(data)


def save_to_cache(data: bytes, file_name: str) -> Path:
    ATTACHMENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file_name)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = ATTACHMENT_CACHE_DIR / f"{ts}_{safe_name}"
    path.write_bytes(data)
    return path


def process_attachment(
    db: Session,
    file_url: str,
    raw_document_id: int | None = None,
    source_url: str = "",
) -> BidAttachment:
    """Download, extract, and persist one attachment. Never raises."""
    file_type = _classify_file_type(file_url)
    file_name = _filename_from_url(file_url)

    attachment = BidAttachment(
        raw_document_id=raw_document_id,
        source_url=source_url,
        file_url=file_url,
        file_name=file_name,
        file_type=file_type,
        parse_status="pending",
    )
    db.add(attachment)
    db.flush()

    data, err = download_attachment(file_url)
    if err:
        attachment.parse_status = "download_failed"
        attachment.error_message = err
        db.flush()
        return attachment
    if data is None:
        attachment.parse_status = "download_failed"
        attachment.error_message = "empty response body"
        db.flush()
        return attachment

    attachment.file_size = len(data)
    try:
        local_path = save_to_cache(data, file_name)
        attachment.local_path = str(local_path)
    except Exception as exc:
        logger.warning("Attachment cache write failed: %s", exc)

    if file_type in ("unknown",):
        attachment.parse_status = "unsupported_type"
        attachment.error_message = f"Unknown file type for URL: {file_url}"
        db.flush()
        return attachment

    try:
        text = extract_text(data, file_type)
        attachment.extracted_text = text[:1_000_000]  # cap at ~1 MB
        attachment.parse_status = "parsed"
    except Exception as exc:
        attachment.parse_status = "parse_failed"
        attachment.error_message = str(exc)[:2000]

    db.flush()
    return attachment


def discover_and_process_attachments_for_raw_doc(
    db: Session, raw_doc: BidRawDocument
) -> list[BidAttachment]:
    """Discover attachments in a raw document's HTML and process them."""
    if not raw_doc.html_content:
        return []

    links = discover_attachment_links(raw_doc.html_content, raw_doc.source_url)
    if not links:
        return []

    results: list[BidAttachment] = []
    for file_url, _label in links:
        attachment = process_attachment(
            db,
            file_url=file_url,
            raw_document_id=raw_doc.id,
            source_url=raw_doc.source_url,
        )
        results.append(attachment)
    return results


def process_pending_attachments(db: Session, limit: int = 20) -> int:
    """Process attachments that are still pending download/parse."""
    pending = list(
        db.scalars(
            select(BidAttachment)
            .where(BidAttachment.parse_status == "pending")
            .limit(limit)
        )
    )
    if not pending:
        # Also try discovering attachments from raw documents without any
        raw_docs = list(
            db.scalars(
                select(BidRawDocument)
                .where(
                    ~BidRawDocument.attachments.any(),
                    BidRawDocument.html_content.is_not(None),
                )
                .limit(limit)
            )
        )
        for raw_doc in raw_docs:
            discover_and_process_attachments_for_raw_doc(db, raw_doc)
        return len(raw_docs)

    processed = 0
    for attachment in pending:
        try:
            data, err = download_attachment(attachment.file_url)
            if err:
                attachment.parse_status = "download_failed"
                attachment.error_message = err
                continue
            if data is None:
                attachment.parse_status = "download_failed"
                attachment.error_message = "empty response body"
                continue
            attachment.file_size = len(data)
            text = extract_text(data, attachment.file_type)
            attachment.extracted_text = text[:1_000_000]
            attachment.parse_status = "parsed"
            processed += 1
        except Exception as exc:
            attachment.parse_status = "parse_failed"
            attachment.error_message = str(exc)[:2000]
    db.flush()
    return processed


def attachment_text_for_raw_doc(db: Session, raw_document_id: int) -> str:
    """Collect all extracted text from attachments for a raw document."""
    attachments = list(
        db.scalars(
            select(BidAttachment)
            .where(
                BidAttachment.raw_document_id == raw_document_id,
                BidAttachment.parse_status == "parsed",
                BidAttachment.extracted_text.is_not(None),
            )
        )
    )
    parts: list[str] = []
    for att in attachments:
        if att.extracted_text:
            parts.append(f"[Attachment: {att.file_name} ({att.file_type})]\n{att.extracted_text}")
    return "\n\n".join(parts)


def enhanced_extract_from_attachment_text(text: str, title: str, publish_date) -> dict:
    """Extract structured fields from attachment text using enhanced regex patterns.

    This complements _simple_extract in crawl_service.py with attachment-specific
    patterns for PDF/DOCX/XLSX content.
    """
    import re as _re
    from decimal import Decimal, InvalidOperation

    def _parse_amount(s: str) -> Decimal | None:
        s = s.replace(",", "").replace("，", "").replace(" ", "")
        try:
            return Decimal(s)
        except InvalidOperation:
            return None

    def _between(start: str, end: str) -> str | None:
        if start not in text:
            return None
        after = text.split(start, 1)[1]
        # Split on the end marker or newline (whichever comes first after start)
        pos = after.find(end)
        nl_pos = after.find("\n")
        cutoff = pos if pos >= 0 else len(after)
        if nl_pos >= 0 and nl_pos < cutoff:
            cutoff = nl_pos
        return after[:cutoff].strip() or None

    result: dict = {
        "is_scaffold_related": True,
        "announcement_type": "中标公告" if "中标" in title else "成交公告",
        "project_name": title.replace("中标公告", "").replace("成交结果公告", ""),
        "province": None,
        "city": None,
        "district": None,
        "buyer": _between("采购人：", "。") or _between("招标人：", "。") or _between("采购单位：", "。"),
        "agency": _between("代理机构：", "。") or _between("招标代理：", "。"),
        "winner": _between("中标人：", "。") or _between("成交单位：", "。") or _between("中标单位：", "。"),
        "bid_amount": None,
        "publish_date": publish_date.isoformat() if publish_date else None,
        "scaffold_type": "盘扣" if "盘扣" in text else "扣件式钢管脚手架" if "钢管" in text else "脚手架",
        "procurement_type": "租赁" if "租赁" in text else "专业分包",
        "service_scope": _between("服务范围：", "。") or _between("服务内容：", "。"),
        "duration_text": None,
        "quantity_text": None,
        "area_m2": None,
        "tonnage": None,
        "rental_days": None,
        "pricing_method": "总价折算",
        "unit_price_candidates": [],
        "ai_summary": "附件文本基于规则抽取生成，待 AI/人工复核。",
        "missing_fields": [],
        "raw_evidence_snippets": [],
        "confidence": 0.5,
    }

    # Enhanced amount extraction (handles "3,200,000元", "320万", "386.5万元", "中标金额：3200000")
    amount_patterns = [
        _re.compile(r"(?:中标金额|成交金额|合同金额|投标报价|中标价|成交价)[：:]?\s*(?:人民币)?\s*([0-9,.，]+)\s*(亿元|万元|元)?"),
        _re.compile(r"(?:金额|报价)[：:]?\s*(?:人民币)?\s*([0-9,.，]+)\s*(亿元|万元|元)?"),
    ]
    for pat in amount_patterns:
        match = pat.search(text)
        if match:
            value = match.group(1)
            unit = match.group(2) or "元"
            amount = _parse_amount(value)
            if amount:
                if unit == "亿元":
                    amount *= Decimal("100000000")
                elif unit == "万元":
                    amount *= Decimal("10000")
                result["bid_amount"] = amount
                result["confidence"] = max(result["confidence"], 0.7)
            break

    # Enhanced area extraction
    area_patterns = [
        _re.compile(r"(?:脚手架)?(?:工程面积|建筑面积|面积|搭设面积)约?\s*([0-9,.，]+)\s*(?:平方米|㎡|m2)"),
        _re.compile(r"(?:搭设|脚手架).*?([0-9,.，]+)\s*(?:平方米|㎡|m2)"),
    ]
    for pat in area_patterns:
        match = pat.search(text)
        if match:
            area_val = _parse_amount(match.group(1))
            if area_val:
                result["area_m2"] = area_val
                result["confidence"] = max(result["confidence"], 0.6)
            break

    # Tonnage
    ton_match = _re.search(r"(?:吨位|重量|钢材用量?)\s*[：:]?\s*([0-9,.，]+)\s*(?:吨|t)", text)
    if ton_match:
        ton = _parse_amount(ton_match.group(1))
        if ton:
            result["tonnage"] = ton

    # Duration/rental period
    days_match = _re.search(
        r"(?:服务期|租期|工期|租赁期)[：:]?\s*(?:约)?\s*(?:为)?\s*([0-9]+)\s*(?:天|日)",
        text,
    )
    months_match = _re.search(
        r"(?:服务期|租期|工期|租赁期)[：:]?\s*(?:约)?\s*(?:为)?\s*([0-9]+)\s*(?:个?月)",
        text,
    )
    if days_match:
        result["rental_days"] = int(days_match.group(1))
        result["duration_text"] = days_match.group(0)
        result["confidence"] = max(result["confidence"], 0.55)
    elif months_match:
        result["rental_days"] = int(months_match.group(1)) * 30
        result["duration_text"] = months_match.group(0)
        result["confidence"] = max(result["confidence"], 0.55)

    # Unit price extraction (元/㎡, 元/吨/天, 元/月)
    unit_price_patterns = [
        _re.compile(r"([0-9,.，]+)\s*元\s*/\s*(?:平方米|㎡|m2)\s*(?:/|·)?\s*(?:天|日)?"),
        _re.compile(r"([0-9,.，]+)\s*元\s*/\s*(?:吨)\s*(?:/|·)?\s*(?:天|日)"),
        _re.compile(r"([0-9,.，]+)\s*元\s*/\s*(?:月|个?月)"),
        _re.compile(r"([0-9,.，]+)\s*元\s*/\s*(?:吨)"),
    ]
    for i, pat in enumerate(unit_price_patterns):
        match = pat.search(text)
        if match:
            price = _parse_amount(match.group(1))
            if price:
                if i == 0:
                    unit = "元/㎡/天" if any(m in text for m in ("天", "日")) else "元/㎡"
                elif i == 1:
                    unit = "元/吨/天"
                elif i == 2:
                    unit = "元/月"
                else:
                    unit = "元/吨"
                result["unit_price_candidates"].append({"price": price, "unit": unit})
                result["snippet_" + unit] = match.group(0)

    return result
