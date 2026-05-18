import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import PublicBidCrawler, RawBidDocument

USER_AGENT = "building-price-intel/0.1 (+public-data; contact: local-development)"


class BlockedReason(StrEnum):
    PUBLIC_PAGE_REACHABLE = "public_page_reachable"
    PUBLIC_API_FOUND = "public_api_found"
    NO_KEYWORD_HITS = "no_keyword_hits"
    PARSER_NO_MATCH = "parser_no_match"
    JS_RENDER_REQUIRED = "js_render_required"
    BLOCKED_403 = "blocked_403"
    CAPTCHA_REQUIRED = "captcha_required"
    LOGIN_REQUIRED = "login_required"
    PAID_CONTENT = "paid_content"
    TRANSPORT_ERROR = "transport_error"


class BlockedSourceError(RuntimeError):
    def __init__(self, reason: BlockedReason | str, message: str | None = None) -> None:
        self.reason = BlockedReason(reason)
        super().__init__(message or self.reason.value)


def classify_blocked_response(response) -> BlockedReason | None:
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    lower = text.lower()
    if status_code == 403:
        return BlockedReason.BLOCKED_403
    if any(marker in lower for marker in ("captcha", "验证码", "滑块验证", "人机验证")):
        return BlockedReason.CAPTCHA_REQUIRED
    if any(marker in lower for marker in ("登录", "登陆", "login", "sign in", "password")) and ("password" in lower or "登录" in lower or "login" in lower):
        return BlockedReason.LOGIN_REQUIRED
    if any(marker in lower for marker in ("付费", "会员", "订阅", "paywall", "paid content")):
        return BlockedReason.PAID_CONTENT
    return None


def _raise_if_blocked(response) -> None:
    reason = classify_blocked_response(response)
    if reason is not None:
        raise BlockedSourceError(reason)


@dataclass(frozen=True)
class PublicPriceRow:
    source_name: str
    source_url: str
    date: date
    category: str
    region: str
    city: str | None
    product_name: str
    spec: str | None
    material: str | None
    unit: str
    price: Decimal
    change_value: Decimal | None = None
    tax_included: bool = True


class BusinessSocietyPriceCrawler:
    """Best-effort parser/fetcher for public commodity price pages.

    The default source is 生意社/100ppi public pages. The parser is intentionally
    conservative: it only emits rows when product, date, numeric price, city and
    unit are visible in public page text/table content.
    """

    source_name = "生意社公开价格页"
    base_url = "https://www.100ppi.com"
    source_urls = (
        "https://www.100ppi.com/price/",
    )

    def fetch_prices(self) -> list[PublicPriceRow]:
        rows: list[PublicPriceRow] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            for url in self.source_urls:
                response = client.get(url)
                _raise_if_blocked(response)
                response.raise_for_status()
                rows.extend(self.parse_prices(response.text, source_url=str(response.url)))
        return rows

    def parse_prices(self, html: str, source_url: str) -> list[PublicPriceRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[PublicPriceRow] = []
        for tr in soup.find_all("tr"):
            text = " ".join(cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"]))
            row = self._parse_line(text, source_url)
            if row:
                rows.append(row)
        if rows:
            return rows
        for line in soup.get_text("\n", strip=True).splitlines():
            row = self._parse_line(line, source_url)
            if row:
                rows.append(row)
        return _dedupe_prices(rows)

    def _parse_line(self, text: str, source_url: str) -> PublicPriceRow | None:
        if not any(name in text for name in ("螺纹钢", "废钢", "重废", "盘扣", "脚手架")):
            return None
        parsed_date = _parse_date(text) or date.today()
        price = _parse_price(text)
        if price is None:
            return None
        product_name, category = _classify_product(text)
        city = _detect_city(text)
        region = _region_for_city(city)
        unit = _detect_unit(text)
        spec = _detect_spec(text)
        material = "HRB400E" if "HRB400E" in text else "废钢" if product_name in {"重废", "废钢"} else "Q355" if "盘扣" in product_name else None
        return PublicPriceRow(
            source_name=self.source_name,
            source_url=source_url,
            date=parsed_date,
            category=category,
            region=region,
            city=city,
            product_name=product_name,
            spec=spec,
            material=material,
            unit=unit,
            price=price,
            tax_included=True,
        )


class ChinaGovernmentProcurementCrawler(PublicBidCrawler):
    source_name = "中国政府采购网"
    base_url = "http://search.ccgp.gov.cn/bxsearch"

    def search(self, keyword: str) -> list[RawBidDocument]:
        params = {"searchtype": "1", "page_index": "1", "bidSort": "0", "buyerName": "", "projectId": "", "pinMu": "0", "bidType": "0", "dbselect": "bidx", "kw": keyword}
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_search_results(response.text, keyword=keyword, base_url=self.base_url)

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        soup = BeautifulSoup(html, "html.parser")
        docs: list[RawBidDocument] = []
        text = soup.get_text("\n", strip=True)
        for link in soup.find_all("a"):
            title = link.get_text(" ", strip=True)
            if not title or not _is_scaffold_related(title + " " + text, keyword):
                continue
            href = link.get("href") or base_url or self.base_url
            source_url = urljoin(base_url or self.base_url, href)
            surrounding = _surrounding_text(link)
            content = surrounding if len(surrounding) > len(title) else text
            publish_date = _parse_date(content) or _parse_date(title)
            docs.append(
                RawBidDocument(
                    source_name=self.source_name,
                    source_url=source_url,
                    title=title[:512],
                    publish_date=publish_date,
                    region=_detect_province_or_region(content),
                    html_content=str(link.parent) if link.parent else str(link),
                    text_content=content,
                )
            )
        return _dedupe_docs(docs)


class GuangdongPublicResourceTradingCrawler(PublicBidCrawler):
    """Parser/fetcher for 广东省公共资源交易平台 tender notices."""

    source_name = "广东省公共资源交易平台"
    base_url = "https://ygp.gdzwfw.gov.cn"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_search_results(response.text, keyword=keyword, base_url=str(response.url))

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return _parse_public_bid_links(
            html,
            keyword=keyword,
            source_name=self.source_name,
            base_url=base_url or self.base_url,
        )


class GuangdongGovernmentProcurementSmartCloudCrawler(PublicBidCrawler):
    """Parser/fetcher for 广东政府采购智慧云平台 procurement notices."""

    source_name = "广东政府采购智慧云平台"
    base_url = "https://gdgpo.czt.gd.gov.cn"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_search_results(response.text, keyword=keyword, base_url=str(response.url))

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return _parse_public_bid_links(
            html,
            keyword=keyword,
            source_name=self.source_name,
            base_url=base_url or self.base_url,
        )


class GuangzhouPublicResourceTradingCrawler(PublicBidCrawler):
    """Parser/fetcher for 广州公共资源交易平台 tender notices."""

    source_name = "广州公共资源交易平台"
    base_url = "https://www.gzggzy.cn"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_search_results(response.text, keyword=keyword, base_url=str(response.url))

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return _parse_public_bid_links(
            html,
            keyword=keyword,
            source_name=self.source_name,
            base_url=base_url or self.base_url,
        )


def _parse_public_bid_links(html: str, *, keyword: str, source_name: str, base_url: str) -> list[RawBidDocument]:
    soup = BeautifulSoup(html, "html.parser")
    docs: list[RawBidDocument] = []
    page_text = soup.get_text("\n", strip=True)
    for link in soup.find_all("a"):
        title = _clean_text(link.get_text(" ", strip=True))
        if not title:
            continue
        surrounding = _surrounding_text(link)
        content = surrounding if len(surrounding) > len(title) else page_text
        if not _is_scaffold_related(f"{title} {content}", keyword):
            continue
        href = link.get("href") or base_url
        docs.append(
            RawBidDocument(
                source_name=source_name,
                source_url=urljoin(base_url, href),
                title=title[:512],
                publish_date=_parse_date(content) or _parse_date(title),
                region=_detect_province_or_region(content) or _detect_province_or_region(title),
                html_content=str(link.parent) if link.parent else str(link),
                text_content=content,
            )
        )
    return _dedupe_docs(docs)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(text: str) -> date | None:
    match = re.search(r"(20\d{2})[-年./](\d{1,2})[-月./](\d{1,2})", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_price(text: str) -> Decimal | None:
    if "元" not in text:
        return None
    candidates = re.findall(r"(?<!20\d{2}[-年./])(?<!\d)(\d{1,6}(?:\.\d{1,2})?)(?![-月./]\d)", text)
    for value in reversed(candidates):
        try:
            number = Decimal(value)
        except InvalidOperation:
            continue
        if number > 0:
            return number
    return None


def _classify_product(text: str) -> tuple[str, str]:
    if "螺纹钢" in text:
        return "螺纹钢", "steel"
    if "重废" in text:
        return "重废", "scrap"
    if "废钢" in text:
        return "废钢", "scrap"
    if "盘扣" in text:
        return "盘扣式脚手架租赁", "scaffold"
    return "脚手架租赁", "scaffold"


def _detect_city(text: str) -> str | None:
    for city in ("北京", "天津", "上海", "广州", "深圳", "呼和浩特", "乌兰察布", "佛山", "唐山", "杭州", "成都", "重庆"):
        if city in text:
            return city
    return None


def _region_for_city(city: str | None) -> str:
    if city in {"北京", "天津", "唐山"}:
        return "华北"
    if city in {"呼和浩特", "乌兰察布"}:
        return "内蒙古"
    if city in {"广州", "深圳", "佛山"}:
        return "华南"
    if city in {"上海", "杭州"}:
        return "华东"
    if city in {"成都", "重庆"}:
        return "西南"
    return "全国"


def _detect_unit(text: str) -> str:
    if "元/吨/天" in text or "元/吨·天" in text:
        return "元/吨/天"
    if "元/㎡" in text or "元/平方米" in text:
        return "元/㎡"
    if "元/月" in text:
        return "元/月"
    return "元/吨"


def _detect_spec(text: str) -> str | None:
    match = re.search(r"(HRB400E\s*\d+mm|\d+mm以上|48系)", text)
    return match.group(1) if match else None


def _is_scaffold_related(text: str, keyword: str) -> bool:
    keywords = [keyword, "脚手架", "盘扣", "扣件式", "钢管脚手架", "周转材料"]
    return any(item and item in text for item in keywords)


def _detect_province_or_region(text: str) -> str | None:
    if any(city in text for city in ("广州", "深圳", "佛山", "东莞", "中山", "珠海", "惠州", "江门", "肇庆", "南沙", "番禺", "顺德")):
        return "广东"
    for region in ("广东", "内蒙古", "北京", "天津", "上海", "河北", "浙江", "四川", "重庆"):
        if region in text:
            return region
    return None


def _surrounding_text(link) -> str:
    parent = link.parent
    parts: list[str] = []
    if parent:
        parts.append(parent.get_text(" ", strip=True))
        container = parent.parent
        if container and container is not parent:
            parts.append(container.get_text(" ", strip=True))
            container_sibling = container.find_next_sibling()
            if container_sibling:
                parts.append(container_sibling.get_text(" ", strip=True))
        sibling = parent.find_next_sibling()
        if sibling:
            parts.append(sibling.get_text(" ", strip=True))
    return "\n".join(part for part in parts if part)


def _dedupe_prices(rows: list[PublicPriceRow]) -> list[PublicPriceRow]:
    seen: set[tuple] = set()
    result: list[PublicPriceRow] = []
    for row in rows:
        key = (row.date, row.category, row.city, row.product_name, row.spec, row.source_url)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _dedupe_docs(docs: list[RawBidDocument]) -> list[RawBidDocument]:
    seen: set[str] = set()
    result: list[RawBidDocument] = []
    for doc in docs:
        if doc.source_url not in seen:
            seen.add(doc.source_url)
            result.append(doc)
    return result
