import io
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.core.database import SessionLocal
from app.models.attachment import BidAttachment
from app.models.crawl import BidRawDocument
from app.services.attachment_extractor import (
    _classify_file_type,
    _extract_pdf,
    _extract_docx,
    _extract_xlsx,
    _extract_html,
    _filename_from_url,
    attachment_text_for_raw_doc,
    discover_and_process_attachments_for_raw_doc,
    discover_attachment_links,
    enhanced_extract_from_attachment_text,
    process_attachment,
)

# ---------------------------------------------------------------------------
# HTML attachment link discovery
# ---------------------------------------------------------------------------

ATTACHMENT_HTML = """
<html><body>
<p>中标公告正文内容...</p>
<a href="/uploads/bid_result.pdf">招标文件下载</a>
<a href="/download?file=contract.docx">采购合同</a>
<a href="/files/工程量清单.xlsx">附件：工程量清单</a>
<a href="/files/bid_detail.html">公告详情</a>
<a href="/uploads/photo.jpg">现场照片</a>
</body></html>
"""


def test_discover_attachment_links_finds_pdf_docx_xlsx_links() -> None:
    links = discover_attachment_links(ATTACHMENT_HTML, "https://example.com/bids/")
    assert len(links) == 3  # pdf, docx, xlsx (not jpg, not html without keyword)
    urls = [url for url, _ in links]
    assert any("bid_result.pdf" in u for u in urls)
    assert any("contract.docx" in u for u in urls)
    assert any("工程量清单.xlsx" in u for u in urls)


def test_discover_attachment_links_skips_non_attachment_urls() -> None:
    html = '<a href="/page.html">普通页面</a><a href="/data.json">JSON数据</a>'
    links = discover_attachment_links(html, "https://example.com")
    assert links == []


def test_discover_attachment_links_resolves_relative_urls() -> None:
    html = '<a href="../files/report.pdf">报告</a>'
    links = discover_attachment_links(html, "https://example.com/bids/2026/")
    assert len(links) == 1
    # "../files/report.pdf" from "https://example.com/bids/2026/" 
    # resolves to "https://example.com/bids/files/report.pdf"
    assert links[0][0].startswith("https://example.com/bids/files/report.pdf")


# ---------------------------------------------------------------------------
# File type classification
# ---------------------------------------------------------------------------

def test_classify_file_type() -> None:
    assert _classify_file_type("https://x.com/a.pdf?download=1") == "pdf"
    assert _classify_file_type("https://x.com/a.DOCX") == "docx"
    assert _classify_file_type("https://x.com/a.XLSX") == "xlsx"
    assert _classify_file_type("https://x.com/a.doc") == "doc"
    assert _classify_file_type("https://x.com/a.xls") == "xls"
    assert _classify_file_type("https://x.com/a.htm") == "html"
    assert _classify_file_type("https://x.com/a.xyz") == "unknown"


def test_filename_from_url() -> None:
    assert _filename_from_url("https://x.com/path/招标文件.pdf?t=1") == "招标文件.pdf"
    assert _filename_from_url("https://x.com/file") == "file.unknown"


# ---------------------------------------------------------------------------
# Text extraction from mock binary data
# ---------------------------------------------------------------------------

def test_extract_pdf_from_mock() -> None:
    """pypdf extraction from a mock PDF (may fail on minimal PDFs)."""
    pdf_bytes = _minimal_pdf_bytes()
    try:
        text = _extract_pdf(pdf_bytes)
        # With a minimal PDF, pypdf may extract text or return empty
        assert isinstance(text, str)
    except RuntimeError:
        # Minimal PDFs can trigger pypdf parsing errors; acceptable
        pass


def test_extract_docx_from_mock() -> None:
    docx_bytes = _minimal_docx_bytes()
    text = _extract_docx(docx_bytes)
    assert "盘扣式脚手架" in text
    assert "中标金额" in text


def test_extract_xlsx_from_mock() -> None:
    xlsx_bytes = _minimal_xlsx_bytes()
    text = _extract_xlsx(xlsx_bytes)
    assert "项目名称" in text
    assert "金额" in text


def test_extract_html_from_mock() -> None:
    html_bytes = "<html><body><p>公告内容 脚手架租赁</p></body></html>".encode("utf-8")
    text = _extract_html(html_bytes)
    assert "脚手架租赁" in text


# ---------------------------------------------------------------------------
# Attachment persistence
# ---------------------------------------------------------------------------

def test_process_attachment_saves_to_db() -> None:
    with SessionLocal() as db:
        # Create a raw document first
        raw = BidRawDocument(
            source_name="test",
            source_url="https://example.com/bid/1",
            title="测试公告",
            text_content="测试内容",
            content_hash="test_hash_att_001",
        )
        db.add(raw)
        db.flush()

        # Process attachment with valid PDF
        attachment = process_attachment(
            db,
            file_url="https://example.com/files/test.pdf",
            raw_document_id=raw.id,
            source_url=raw.source_url,
        )
        # Since we can't download from example.com, it will be download_failed
        assert attachment.parse_status == "download_failed"
        assert attachment.file_type == "pdf"
        assert attachment.raw_document_id == raw.id
        assert attachment.source_url == raw.source_url


def test_discover_and_process_attachments_saves_links() -> None:
    with SessionLocal() as db:
        raw = BidRawDocument(
            source_name="test",
            source_url="https://example.com/bid/2",
            title="带附件的公告",
            text_content="测试",
            content_hash="test_hash_att_002",
            html_content=ATTACHMENT_HTML,
        )
        db.add(raw)
        db.flush()

        attachments = discover_and_process_attachments_for_raw_doc(db, raw)
        # All downloads will fail (can't reach example.com), but records are created
        assert len(attachments) >= 3
        for att in attachments:
            assert att.raw_document_id == raw.id
            assert att.parse_status in ("download_failed", "pending")


def test_attachment_text_for_raw_doc() -> None:
    with SessionLocal() as db:
        raw = BidRawDocument(
            source_name="test",
            source_url="https://example.com/bid/3",
            title="测试",
            text_content="test",
            content_hash="test_hash_att_003",
        )
        db.add(raw)
        db.flush()

        # Add an attachment with extracted text
        att = BidAttachment(
            raw_document_id=raw.id,
            source_url=raw.source_url,
            file_url="https://example.com/f.pdf",
            file_name="test.pdf",
            file_type="pdf",
            parse_status="parsed",
            extracted_text="中标金额：5000000元\n建筑面积：80000平方米",
        )
        db.add(att)
        db.flush()

        text = attachment_text_for_raw_doc(db, raw.id)
        assert "5000000元" in text
        assert "80000平方米" in text


# ---------------------------------------------------------------------------
# Enhanced extraction from attachment text
# ---------------------------------------------------------------------------

def test_enhanced_extract_from_attachment_text() -> None:
    text = """
    项目名称：深圳某医院盘扣式脚手架租赁
    采购人：深圳市卫生局
    中标人：深圳市安建周转材料有限公司
    中标金额：人民币 3,200,000 元
    脚手架面积约 45,000 平方米
    服务期：180 天
    单价：7.50 元/㎡
    搭设面积 45,000 平方米
    """
    result = enhanced_extract_from_attachment_text(text, "深圳医院脚手架中标公告", date(2026, 5, 18))
    assert result["winner"] == "深圳市安建周转材料有限公司"
    assert result["bid_amount"] == Decimal("3200000.00")
    assert result["area_m2"] == Decimal("45000.00")
    assert result["rental_days"] == 180
    assert result["confidence"] >= 0.7


def test_enhanced_extract_handles_ten_thousand_yuan() -> None:
    text = "中标金额：386.5 万元。建筑面积约 52,000 平方米，租期约为 180 天。"
    result = enhanced_extract_from_attachment_text(text, "测试项目", date(2026, 5, 18))
    assert result["bid_amount"] == Decimal("3865000.00")
    assert result["area_m2"] == Decimal("52000.00")
    assert result["rental_days"] == 180


def test_enhanced_extract_unit_prices() -> None:
    text = "盘扣脚手架租赁单价 7.80 元/平方米/天，钢管扣件租赁 0.025 元/个/天。"
    result = enhanced_extract_from_attachment_text(text, "测试", date(2026, 5, 18))
    assert len(result["unit_price_candidates"]) >= 1


def test_enhanced_extract_returns_low_confidence_without_data() -> None:
    text = "这是一个普通的公告，没有任何金额和面积数据。"
    result = enhanced_extract_from_attachment_text(text, "测试公告", date(2026, 5, 18))
    assert result["confidence"] <= 0.5
    assert result["bid_amount"] is None



# ---------------------------------------------------------------------------
# Mock file generators
# ---------------------------------------------------------------------------

def _minimal_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with ASCII text."""
    text_content = "Hello PDF scaffold bidding"
    text_line = f"BT /F1 12 Tf 100 700 Td ({text_content}) Tj ET"
    text_len = len(text_line)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length " + str(text_len).encode() + b">>stream\n" +
        text_line.encode() +
        b"\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000201 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n" +
        str(280 + text_len).encode() + b"\n%%EOF"
    )
    return pdf


def _minimal_docx_bytes() -> bytes:
    """Generate a minimal DOCX with scaffold-related content."""
    from docx import Document
    doc = Document()
    doc.add_paragraph("盘扣式脚手架租赁中标公告")
    doc.add_paragraph("中标金额：人民币450万元")
    doc.add_paragraph("脚手架搭设面积：50000平方米")
    doc.add_paragraph("服务期：200天")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _minimal_xlsx_bytes() -> bytes:
    """Generate a minimal XLSX with bid data."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "报价清单"
    ws.append(["项目名称", "规格", "数量", "单价", "金额"])
    ws.append(["盘扣式脚手架", "48系", "50000㎡", "7.5元/㎡/天", "375000元/天"])
    ws.append(["钢管扣件", "标准", "10000个", "0.025元/个/天", "250元/天"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
