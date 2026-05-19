import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

import json

from app.crawlers.base import PublicBidCrawler, RawBidDocument

USER_AGENT = "building-price-intel/0.1 (+public-data; contact: local-development)"

# Chinese province code prefix -> province name (from administrative division codes)
PROVINCE_CODE_MAP: dict[str, str] = {
    "11": "北京", "12": "天津", "13": "河北", "14": "山西", "15": "内蒙古",
    "21": "辽宁", "22": "吉林", "23": "黑龙江",
    "31": "上海", "32": "江苏", "33": "浙江", "34": "安徽", "35": "福建", "36": "江西", "37": "山东",
    "41": "河南", "42": "湖北", "43": "湖南",
    "44": "广东", "45": "广西", "46": "海南",
    "50": "重庆", "51": "四川", "52": "贵州", "53": "云南", "54": "西藏",
    "61": "陕西", "62": "甘肃", "63": "青海", "64": "宁夏", "65": "新疆",
}


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
    api_url = "https://ygp.gdzwfw.gov.cn/ggzy-portal/search/v2/items"

    def search(self, keyword: str) -> list[RawBidDocument]:
        payload = {
            "type": "trading-type",
            "openConvert": False,
            "keyword": keyword,
            "siteCode": "44",
            "secondType": "A",
            "tradingProcess": "",
            "thirdType": "[]",
            "projectType": "",
            "publishStartTime": "",
            "publishEndTime": "",
            "pageNo": 1,
            "pageSize": 10,
        }
        headers = {"User-Agent": USER_AGENT, "Referer": "https://ygp.gdzwfw.gov.cn/ggzy-portal/"}
        with httpx.Client(headers=headers, timeout=12, follow_redirects=True) as client:
            response = client.post(self.api_url, json=payload)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_api_response(response.text, keyword=keyword)

    def parse_api_response(self, body: str | dict, keyword: str) -> list[RawBidDocument]:
        payload = json.loads(body) if isinstance(body, str) else body
        items = ((payload or {}).get("data") or {}).get("pageData") or []
        docs: list[RawBidDocument] = []
        for item in items:
            title = _clean_text(str(item.get("noticeTitle") or ""))
            if not title or not _is_scaffold_related(title, keyword):
                continue
            publish_date = _parse_date(str(item.get("publishDate") or ""))
            notice_id = item.get("noticeId") or item.get("docId") or ""
            project_code = item.get("projectCode") or ""
            trading_type = item.get("noticeSecondType") or "A"
            trading_process = item.get("tradingProcess") or ""
            edition = item.get("edition") or "v3"
            if project_code and trading_process:
                source_url = f"{self.base_url}/ggzy-portal/#/44/jygg/{edition}/{project_code}/{trading_type}/{trading_process}"
            else:
                source_url = f"{self.base_url}/ggzy-portal/#/44/jygg/v0/{notice_id}"
            content = "\n".join(
                str(value)
                for value in (
                    title,
                    item.get("noticeSecondTypeDesc"),
                    item.get("noticeThirdTypeDesc"),
                    item.get("projectTypeName"),
                    item.get("siteName"),
                    item.get("regionName"),
                    item.get("datasetName"),
                    item.get("pubServicePlat"),
                    item.get("publishDate"),
                )
                if value
            )
            docs.append(
                RawBidDocument(
                    source_name=self.source_name,
                    source_url=source_url,
                    title=title[:512],
                    publish_date=publish_date,
                    region=_detect_province_or_region(content) or "广东",
                    html_content=json.dumps(item, ensure_ascii=False),
                    text_content=content,
                )
            )
        return _dedupe_docs(docs)

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


class NationalPublicResourcePlatformCrawler(PublicBidCrawler):
    """Parser/fetcher for 全国公共资源交易平台 (ggzy.gov.cn) national aggregate.

    Parses the public homepage listing which aggregates latest bid/tender
    announcements from all provincial platforms. Each announcement link carries
    an administrative division code prefix that maps to its province.
    """

    source_name = "全国公共资源交易平台"
    base_url = "https://www.ggzy.gov.cn"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            return self.parse_homepage_listings(response.text, keyword=keyword)

    def parse_homepage_listings(self, html: str, keyword: str) -> list[RawBidDocument]:
        """Parse ggzy.gov.cn homepage for announcement listing links.

        Announcement links follow pattern:
        /information/deal/html/a/{province_code}/{type}/{date}/{hash}.html
        where province_code is a 6-digit administrative code (e.g. 440000 = 广东).
        """
        soup = BeautifulSoup(html, "html.parser")
        docs: list[RawBidDocument] = []
        link_re = re.compile(r"/information/(?:deal|html)/html/a/(\d{6})/")

        for link in soup.find_all("a", href=True):
            href = str(link.get("href", "") or "")
            title = _clean_text(link.get_text(" ", strip=True))
            if not title:
                continue

            # Only process deal announcement links
            match = link_re.search(href)
            if not match:
                continue

            # Build a contained text context from the immediate parent only
            # (avoid _surrounding_text which crawls too far up the DOM tree)
            parent = link.parent
            container_text = parent.get_text(" ", strip=True) if parent else title
            combined = f"{title} {container_text}"

            # Check keyword relevance
            if not _is_scaffold_related(combined, keyword):
                continue

            province_code = match.group(1)
            province = _province_from_code(province_code)
            source_url = urljoin(self.base_url, href)
            publish_date = _parse_date(container_text) or _parse_date(title)

            docs.append(
                RawBidDocument(
                    source_name=self.source_name,
                    source_url=source_url,
                    title=title[:512],
                    publish_date=publish_date,
                    region=province or _detect_province_or_region(combined),
                    html_content=str(parent) if parent else str(link),
                    text_content=container_text,
                )
            )
        return _dedupe_docs(docs)

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return self.parse_homepage_listings(html, keyword=keyword)


class ChinaBiddingPublicServiceCrawler(PublicBidCrawler):
    """Parser/fetcher for 中国招标投标公共服务平台 / 全国招标公告公示搜索引擎.

    The public search engine at ctbpsp.com is a Vue/Element UI SPA.
    The accessible homepage renders announcements via JS XHR/fetch calls.

    Strategy:
    1. Attempt httpx parse of static homepage links (best-effort, may yield little).
    2. If blocked or JS-rendered-only, flag as JS_RENDER_REQUIRED for browser discovery.
    """

    source_name = "中国招标投标公共服务平台"
    base_url = "https://ctbpsp.com"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            text = response.text
            # The SPA homepage is JS-rendered; static content is minimal.
            # Accept sparse results as best-effort with httpx.
            return self.parse_search_results(text, keyword=keyword, base_url=str(response.url))

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return _parse_public_bid_links(
            html,
            keyword=keyword,
            source_name=self.source_name,
            base_url=base_url or self.base_url,
        )


class CentralGovernmentProcurementCrawler(PublicBidCrawler):
    """Parser/fetcher for 中央政府采购网 (zycg.gov.cn).

    The site is a FreeCMS-based SPA. All REST API paths explored return 404;
    the homepage always renders the same index.html regardless of path.
    This parser attempts best-effort HTML extraction from the homepage,
    flagging JS_RENDER_REQUIRED when no keyword-relevant links are found.
    """

    source_name = "中央政府采购网"
    base_url = "https://www.zycg.gov.cn"

    def search(self, keyword: str) -> list[RawBidDocument]:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=12, follow_redirects=True) as client:
            response = client.get(self.base_url)
            _raise_if_blocked(response)
            response.raise_for_status()
            text = response.text
            # The site is a JS-rendered SPA; static HTML extraction is minimal.
            return self.parse_search_results(text, keyword=keyword, base_url=str(response.url))

    def parse_search_results(self, html: str, keyword: str, base_url: str | None = None) -> list[RawBidDocument]:
        return _parse_public_bid_links(
            html,
            keyword=keyword,
            source_name=self.source_name,
            base_url=base_url or self.base_url,
        )


def _province_from_code(code: str) -> str | None:
    prefix2 = code[:2]
    prefix4 = code[:4]
    # Try 2-digit prefix first (covers all provinces)
    if prefix2 in PROVINCE_CODE_MAP:
        return PROVINCE_CODE_MAP[prefix2]
    return None


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
    # Require visible date separators so amounts such as 3200000元 do not get
    # misread as an invalid 2000-0-0 date before the real publish date.
    for match in re.finditer(r"(20\d{2})[-年./](\d{1,2})[-月./](\d{1,2})", text):
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            continue
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
