from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.crawlers.real_public_sources import (
    BusinessSocietyPriceCrawler,
    CentralGovernmentProcurementCrawler,
    ChinaBiddingPublicServiceCrawler,
    ChinaGovernmentProcurementCrawler,
    GuangdongGovernmentProcurementSmartCloudCrawler,
    GuangdongPublicResourceTradingCrawler,
    GuangzhouPublicResourceTradingCrawler,
    NationalPublicResourcePlatformCrawler,
)
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

GUANGDONG_PUBLIC_RESOURCE_HTML = """
<html><body>
<div class="notice-item">
<a href="/ggzy-portal/#/44/jygg/details?id=gd001">佛山市顺德区学校盘扣式脚手架租赁项目中标候选人公示</a>
<span>交易类型：工程建设</span><span>发布日期：2026-05-17</span>
<p>广东省佛山市，采购脚手架、周转材料租赁服务，中标金额：218.6万元。</p>
</div>
</body></html>
"""

GUANGDONG_SMART_CLOUD_HTML = """
<html><body>
<ul>
<li>
<a href="/freecms/site/gd/ggxx/info/2026/8a7ebe001.htm">广州市番禺区市政维护项目扣件式钢管脚手架采购成交公告</a>
<div>广东政府采购智慧云平台 发布时间：2026年05月16日 成交金额：96.2万元。</div>
</li>
</ul>
</body></html>
"""

GUANGZHOU_PUBLIC_RESOURCE_HTML = """
<html><body>
<table>
<tr><td><a href="/jyxx/jsgcZbgg/100001.jhtml">广州南沙综合楼盘扣脚手架专业分包中标结果公告</a></td><td>2026/05/15</td></tr>
<tr><td colspan="2">地点：广州市南沙区。中标价：3880000元。服务内容：模板脚手架工程。</td></tr>
</table>
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


def test_guangdong_public_resource_trading_parser_extracts_bid_documents() -> None:
    crawler = GuangdongPublicResourceTradingCrawler()
    docs = crawler.parse_search_results(GUANGDONG_PUBLIC_RESOURCE_HTML, keyword="脚手架")

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_name == "广东省公共资源交易平台"
    assert doc.source_url.startswith("https://ygp.gdzwfw.gov.cn")
    assert "盘扣式脚手架租赁" in doc.title
    assert doc.publish_date == date(2026, 5, 17)
    assert doc.region == "广东"
    assert "218.6万元" in doc.text_content


def test_guangdong_smart_cloud_parser_extracts_government_procurement_documents() -> None:
    crawler = GuangdongGovernmentProcurementSmartCloudCrawler()
    docs = crawler.parse_search_results(GUANGDONG_SMART_CLOUD_HTML, keyword="脚手架")

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_name == "广东政府采购智慧云平台"
    assert doc.source_url.startswith("https://gdgpo.czt.gd.gov.cn")
    assert "扣件式钢管脚手架" in doc.title
    assert doc.publish_date == date(2026, 5, 16)
    assert doc.region == "广东"
    assert "96.2万元" in doc.text_content


def test_guangzhou_public_resource_trading_parser_extracts_bid_documents() -> None:
    crawler = GuangzhouPublicResourceTradingCrawler()
    docs = crawler.parse_search_results(GUANGZHOU_PUBLIC_RESOURCE_HTML, keyword="脚手架")

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_name == "广州公共资源交易平台"
    assert doc.source_url.startswith("https://www.gzggzy.cn")
    assert "盘扣脚手架专业分包" in doc.title
    assert doc.publish_date == date(2026, 5, 15)
    assert doc.region == "广东"
    assert "3880000元" in doc.text_content


def test_run_public_crawl_saves_real_public_prices_and_bid_docs() -> None:
    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="脚手架", price_html=PRICE_HTML, bid_html=BID_HTML)
        assert task.status == "success"
        assert task.total_found >= 4
        assert task.total_saved >= 3

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


NATIONAL_PUBLIC_RESOURCE_HTML = """
<html><body>
<div class="main-list">
  <ul>
    <li>
      <a href="/information/deal/html/a/440000/0104/20260518/0044abc123def456deadbeef20260518.html">广州市某工程项目盘扣式脚手架租赁中标候选人公示</a>
      <span>2026-05-18</span>
    </li>
    <li>
      <a href="/information/deal/html/a/510000/0202/20260517/0051def789ghi012deadbeef20260517.html">成都市某学校项目钢管脚手架采购成交结果公告</a>
      <span>2026-05-17</span>
    </li>
    <li>
      <a href="/information/deal/html/a/320000/0101/20260516/0032ghi345jkl678deadbeef20260516.html">南京市某商业中心扣件式脚手架搭拆专业分包招标公告</a>
      <span>2026-05-16</span>
    </li>
    <li>
      <a href="/information/deal/html/a/130000/0201/20260518/0013jkl901mno234deadbeef20260518.html">石家庄市某医院装修工程招标公告</a>
      <span>2026-05-18</span>
    </li>
  </ul>
</div>
</body></html>
"""

CTBPSP_HOMEPAGE_HTML = """
<html><body>
<div class="el-container">
  <ul class="bulletin-list">
    <li>
      <a href="/bulletin/detail/12345">广东省深圳市周转材料租赁服务中标公告</a>
      <p>发布时间：2026-05-18 中标金额：450万元</p>
    </li>
    <li>
      <a href="/bulletin/detail/12346">北京市某大学教学楼建设工程招标公告</a>
      <p>发布时间：2026-05-17</p>
    </li>
  </ul>
</div>
</body></html>
"""

ZYCG_HOMEPAGE_HTML = """
<html><body>
<div class="container">
  <div class="list">
    <ul>
      <li>
        <a href="/freecms/site/zygjjgzfcgzx/ggxx/info/2026/12345.htm">中央国家机关某部门盘扣式脚手架采购项目中标公告</a>
        <span>发布日期：2026-05-18</span>
      </li>
    </ul>
  </div>
</div>
</body></html>
"""


def test_national_public_resource_platform_parses_ggzy_homepage() -> None:
    crawler = NationalPublicResourcePlatformCrawler()
    docs = crawler.parse_homepage_listings(NATIONAL_PUBLIC_RESOURCE_HTML, keyword="脚手架")
    assert len(docs) == 3
    gd = [d for d in docs if d.region == "广东"][0]
    assert gd.source_name == "全国公共资源交易平台"
    assert "盘扣式脚手架租赁" in gd.title
    assert "440000" in gd.source_url
    assert gd.publish_date == date(2026, 5, 18)
    sc = [d for d in docs if d.region == "四川"][0]
    assert "钢管脚手架" in sc.title
    assert "510000" in sc.source_url
    js = [d for d in docs if d.region == "江苏"][0]
    assert "扣件式脚手架" in js.title


def test_national_public_resource_platform_skips_non_scaffold_links() -> None:
    """Non-scaffold announcement links from ggzy.gov.cn are filtered out."""
    html = """<html><body>
    <ul>
    <li><a href="/information/deal/html/a/440000/0202/20260518/hash1.html">某市办公设备采购公告</a><span>2026-05-18</span></li>
    <li><a href="/information/deal/html/a/440000/0101/20260518/hash2.html">某市盘扣脚手架租赁招标</a><span>2026-05-18</span></li>
    </ul>
    </body></html>"""
    crawler = NationalPublicResourcePlatformCrawler()
    docs = crawler.parse_homepage_listings(html, keyword="脚手架")
    assert len(docs) == 1
    assert "盘扣" in docs[0].title


def test_china_bidding_public_service_parses_ctbpsp_links() -> None:
    crawler = ChinaBiddingPublicServiceCrawler()
    docs = crawler.parse_search_results(CTBPSP_HOMEPAGE_HTML, keyword="周转材料")
    assert len(docs) >= 1
    doc = docs[0]
    assert doc.source_name == "中国招标投标公共服务平台"
    assert "周转材料租赁" in doc.title
    assert doc.source_url.startswith("https://ctbpsp.com")


def test_central_government_procurement_parses_zycg_links() -> None:
    crawler = CentralGovernmentProcurementCrawler()
    docs = crawler.parse_search_results(ZYCG_HOMEPAGE_HTML, keyword="盘扣")
    assert len(docs) >= 1
    doc = docs[0]
    assert doc.source_name == "中央政府采购网"
    assert "盘扣式脚手架" in doc.title
    assert doc.source_url.startswith("https://www.zycg.gov.cn")
    assert doc.publish_date == date(2026, 5, 18)


def test_run_public_crawl_includes_national_aggregate_sources() -> None:
    """National aggregate sources are registered as default bid configs and callable."""
    from app.services.crawl_service import DEFAULT_BID_SOURCE_CONFIGS, BID_CRAWLER_REGISTRY, _enabled_bid_source_configs

    # Verify registry includes all national sources
    for name in ("NationalPublicResourcePlatformCrawler", "ChinaBiddingPublicServiceCrawler", "CentralGovernmentProcurementCrawler"):
        assert name in BID_CRAWLER_REGISTRY, f"Missing {name} in BID_CRAWLER_REGISTRY"

    # Verify default configs include national sources
    configs = _enabled_bid_source_configs(None, include_default_sources=True)
    parser_names = {c["parser_name"] for c in configs if c.get("parser_name")}
    for name in ("NationalPublicResourcePlatformCrawler", "ChinaGovernmentProcurementCrawler", "ChinaBiddingPublicServiceCrawler", "CentralGovernmentProcurementCrawler"):
        assert name in parser_names, f"Missing {name} in enabled bid source configs"

    # Verify sources are persisted after a crawl with HTML
    with SessionLocal() as db:
        task = run_public_crawl(db, keyword="脚手架", price_html=PRICE_HTML, bid_html=BID_HTML)
        assert task.status == "success"
        source_names = set(db.scalars(select(CrawlSource.name)).all())
        for name in ("全国公共资源交易平台", "中国政府采购网", "中国招标投标公共服务平台", "中央政府采购网"):
            assert name in source_names, f"Expected source {name} in CrawlSource table"
