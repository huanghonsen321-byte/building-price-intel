
import re
from datetime import UTC, date, datetime
from decimal import Decimal

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from price_crawler.items import StandardCrawlerItem


class PublicPricesSpider(CrawlSpider):
    name = "public_prices"
    allowed_domains = ["100ppi.com", "ccgp.gov.cn"]
    start_urls = ["https://www.100ppi.com/price/", "http://search.ccgp.gov.cn/bxsearch?searchtype=1&kw=%E8%84%9A%E6%89%8B%E6%9E%B6"]
    rules = (Rule(LinkExtractor(allow=(r"price", r"cggg", r"zbgg")), callback="parse_public_page", follow=True),)

    custom_settings = {"CLOSESPIDER_PAGECOUNT": 50}

    def parse_start_url(self, response):
        yield from self.parse_public_page(response)

    def parse_public_page(self, response):
        text = " ".join(response.css("body ::text").getall())
        for row in response.css("tr"):
            row_text = " ".join(row.css("::text").getall())
            item = self._parse_price(row_text, response.url)
            if item:
                yield item
        if "脚手架" in text or "盘扣" in text:
            title = response.css("title::text").get() or response.css("a::text").get() or "公开招投标公告"
            yield StandardCrawlerItem(record_type="bid", source_name="Scrapy公开公告源", source_url=response.url, crawl_time=datetime.now(UTC), publish_time=_parse_date(text), region=_detect_region(text), city=_detect_city(text), product_name="盘扣" if "盘扣" in text else "脚手架", title=title.strip(), text_content=text[:10000], html_content=response.text[:20000], amount=_parse_amount(text), extra={"confidence": 0.5})

    def _parse_price(self, text: str, url: str):
        if not any(k in text for k in ["螺纹钢", "重废", "废钢", "盘扣", "脚手架"]):
            return None
        price = _parse_price(text)
        if price is None:
            return None
        product, category = _classify(text)
        return StandardCrawlerItem(record_type="price", source_name="Scrapy公开价格源", source_url=url, crawl_time=datetime.now(UTC), publish_time=_parse_date(text) or date.today(), category=category, region=_detect_region(text), city=_detect_city(text), product_name=product, specification=_detect_spec(text), unit=_detect_unit(text), price=price, extra={"tax_included": True})


def _parse_date(text):
    m = re.search(r"(20\d{2})[-年./](\d{1,2})[-月./](\d{1,2})", text)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _parse_price(text):
    if "元" not in text:
        return None
    nums = re.findall(r"(?<!20\d{2}[-年./])(?<!\d)(\d{1,7}(?:\.\d{1,2})?)(?![-月./]\d)", text)
    return Decimal(nums[-1]) if nums else None


def _parse_amount(text):
    m = re.search(r"(?:中标金额|成交金额)：?(\d+(?:\.\d+)?)元", text)
    return Decimal(m.group(1)) if m else None


def _classify(text):
    if "螺纹钢" in text: return "螺纹钢", "steel"
    if "重废" in text: return "重废", "scrap"
    if "废钢" in text: return "废钢", "scrap"
    return "盘扣式脚手架租赁" if "盘扣" in text else "脚手架租赁", "scaffold"


def _detect_city(text):
    for city in ["北京", "天津", "呼和浩特", "乌兰察布", "深圳", "广州", "佛山"]:
        if city in text: return city
    return None


def _detect_region(text):
    city = _detect_city(text)
    if city in ["北京", "天津"]: return "华北"
    if city in ["呼和浩特", "乌兰察布"]: return "内蒙古"
    if city in ["深圳", "广州", "佛山"]: return "华南"
    return "全国"


def _detect_unit(text):
    if "元/吨/天" in text: return "元/吨/天"
    if "元/㎡" in text or "元/平方米" in text: return "元/㎡"
    return "元/吨"


def _detect_spec(text):
    m = re.search(r"(HRB400E\s*\d+mm|\d+mm以上|48系)", text)
    return m.group(1) if m else None
