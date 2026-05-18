from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.crawlers.real_public_sources import BusinessSocietyPriceCrawler, ChinaGovernmentProcurementCrawler
from app.models.crawl import BidRawDocument, CrawlSource
from app.models.price import PriceDaily
from app.services.crawl_service import run_public_crawl


PRICE_HTML = """
<html><body>
<table>
<tr><td>2026-05-18</td><td>螺纹钢</td><td>HRB400E 20mm</td><td>北京</td><td>3560</td><td>元/吨</td></tr>
<tr><td>2026-05-18</td><td>重废</td><td>6mm以上</td><td>天津</td><td>2430</td><td>元/吨</td></tr>
<tr><td>2026-05-18</td><td>盘扣式脚手架租赁</td><td>48系</td><td>呼和浩特</td><td>7.20</td><td>元/吨/天</td></tr>
</table>
</body></html>
"""

BID_HTML = """
<html><body>
<a href="/cggg/dfgg/zbgg/202605/t20260518_001.htm">广东省深圳市医院项目盘扣式脚手架租赁服务中标公告</a>
<p>采购人：深圳市建设发展有限公司。中标人：深圳市安建周转材料有限公司。中标金额：3200000元。
工程量：脚手架面积50000平方米。服务期：200天。发布时间：2026-05-18。</p>
</body></html>
"""


def test_business_society_price_parser_extracts_public_price_rows() -> None:
    crawler = BusinessSocietyPriceCrawler()
    rows = crawler.parse_prices(PRICE_HTML, source_url="https://www.100ppi.com/example.html")

    assert len(rows) == 3
    steel = rows[0]
    assert steel.source_name == "生意社公开价格页"
    assert steel.category == "steel"
    assert steel.product_name == "螺纹钢"
    assert steel.region == "华北"
    assert steel.city == "北京"
    assert steel.price == Decimal("3560")
    assert steel.source_url == "https://www.100ppi.com/example.html"


def test_china_government_procurement_parser_extracts_bid_documents() -> None:
    crawler = ChinaGovernmentProcurementCrawler()
    docs = crawler.parse_search_results(BID_HTML, keyword="脚手架", base_url="http://search.ccgp.gov.cn/bxsearch")

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_name == "中国政府采购网"
    assert doc.source_url.startswith("http://search.ccgp.gov.cn")
    assert "盘扣式脚手架租赁" in doc.title
    assert doc.publish_date == date(2026, 5, 18)
    assert "中标金额：3200000元" in doc.text_content


def test_run_public_crawl_saves_real_public_prices_and_bid_docs() -> None:
    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="脚手架", price_html=PRICE_HTML, bid_html=BID_HTML)
        assert task.status == "success"
        assert task.total_found >= 4
        assert task.total_saved >= 4

        price = db.scalar(select(PriceDaily).where(PriceDaily.source_name == "生意社公开价格页", PriceDaily.product_name == "螺纹钢"))
        assert price is not None
        assert price.source_url and price.source_url.startswith("https://www.100ppi.com")

        raw = db.scalar(select(BidRawDocument).where(BidRawDocument.source_name == "中国政府采购网"))
        assert raw is not None
        assert raw.source_url.startswith("http://search.ccgp.gov.cn")

        source_types = set(db.scalars(select(CrawlSource.source_type)).all())
        assert "real_public_price" in source_types
        assert "real_public_bid" in source_types


def test_run_public_crawl_parses_ten_thousand_yuan_and_approx_area() -> None:
    bid_html = """
    <html><body>
    <a href="/cggg/dfgg/zbgg/202605/t20260518_002.htm">广东省深圳市学校项目盘扣式脚手架租赁服务中标公告</a>
    <p>采购人：深圳市教育建设有限公司。中标人：深圳市周转材料有限公司。
    中标金额：人民币 386.5 万元。工程面积约 52,000 平方米，租期约为 180 天。发布时间：2026-05-18。</p>
    </body></html>
    """

    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="脚手架", price_html="<html></html>", bid_html=bid_html)
        assert task.status == "success"

        raw = db.scalar(select(BidRawDocument).where(BidRawDocument.source_url.like("%t20260518_002%")))
        assert raw is not None
        case = raw.bid_case
        assert case is not None
        assert case.bid_amount == Decimal("3865000.00")
        assert case.area_m2 == Decimal("52000.00")
        assert case.rental_days == 180
        assert case.price_references
        assert case.price_references[0].calculated_price == Decimal("74.33")
