#!/usr/bin/env python
"""Crawlee-compatible public page crawler adapter.

Usage:
  python run_crawlee.py --start-url "https://example.com/steel-prices" --output-db "../output.db"

The script writes normalized crawler records into the backend database via
app.crawlers.standard_output. It intentionally avoids login, CAPTCHA bypass and
paid content. If Playwright rendering is needed, install Crawlee's Playwright
extras and pass --render-js; otherwise it uses httpx for stable public pages.
"""

import argparse
import asyncio
import logging
import random
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.crawlers.standard_output import StandardCrawlerRecord, write_standard_records

LOG = logging.getLogger("crawlee_public_adapter")


async def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    html = await fetch(args.start_url, render_js=args.render_js, proxy=args.proxy)
    records = parse_records(html, args.start_url, args.source_name)
    with SessionLocal() as db:
        created, failed = write_standard_records(db, records)
    LOG.info("crawlee run complete url=%s records=%s created=%s failed=%s output_db=%s", args.start_url, len(records), created, failed, args.output_db)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-url", required=True)
    parser.add_argument("--output-db", default="../output.db", help="Kept for Crawlee CLI compatibility; SQLAlchemy DATABASE_URL controls backend DB output.")
    parser.add_argument("--source-name", default="Crawlee公开数据源")
    parser.add_argument("--render-js", action="store_true", help="Use Crawlee PlaywrightCrawler when available; otherwise falls back to httpx.")
    parser.add_argument("--proxy", default=None, help="Optional HTTP proxy URL. Do not use proxies to bypass access controls.")
    return parser.parse_args()


async def fetch(url: str, *, render_js: bool, proxy: str | None) -> str:
    await asyncio.sleep(random.uniform(1, 3))
    if render_js:
        rendered = await try_playwright_crawlee(url, proxy=proxy)
        if rendered:
            return rendered
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=True, proxy=proxy) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def try_playwright_crawlee(url: str, proxy: str | None = None) -> str | None:
    try:
        from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
    except Exception as exc:
        LOG.warning("Crawlee Playwright unavailable, falling back to httpx: %s", exc)
        return None
    pages: list[str] = []
    crawler = PlaywrightCrawler(max_request_retries=2, max_requests_per_crawl=1, proxy_configuration=None)

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:
        await context.page.wait_for_load_state("networkidle")
        pages.append(await context.page.content())

    await crawler.run([url])
    return pages[0] if pages else None


def parse_records(html: str, source_url: str, source_name: str) -> list[StandardCrawlerRecord]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    records: list[StandardCrawlerRecord] = []
    for tr in soup.find_all("tr"):
        line = " ".join(tr.get_text(" ", strip=True).split())
        price = parse_price(line)
        if price is None:
            continue
        product, category = classify(line)
        records.append(StandardCrawlerRecord(record_type="price", source_name=source_name, source_url=source_url, crawl_time=datetime.now(UTC), publish_time=parse_date(line) or date.today(), category=category, region=detect_region(line), city=detect_city(line), product_name=product, specification=detect_spec(line), unit=detect_unit(line), price=price, extra={"tax_included": True}))
    if any(k in text for k in ["脚手架", "盘扣", "中标", "成交"]):
        amount = parse_amount(text)
        if amount is not None or "脚手架" in text or "盘扣" in text:
            records.append(StandardCrawlerRecord(record_type="bid", source_name=source_name, source_url=source_url, crawl_time=datetime.now(UTC), publish_time=parse_date(text), region=detect_region(text), city=detect_city(text), product_name="盘扣" if "盘扣" in text else "脚手架", type="中标公告" if "中标" in text else "成交公告", title=(soup.title.get_text(strip=True) if soup.title else "公开公告"), text_content=text[:10000], html_content=html[:20000], amount=amount, extra={"confidence": 0.5}))
    return records


def parse_date(text: str):
    m = re.search(r"(20\d{2})[-年./](\d{1,2})[-月./](\d{1,2})", text)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_price(text: str):
    if "元" not in text or not any(k in text for k in ["螺纹钢", "重废", "废钢", "盘扣", "脚手架"]):
        return None
    nums = re.findall(r"(?<!20\d{2}[-年./])(?<!\d)(\d{1,7}(?:\.\d{1,2})?)(?![-月./]\d)", text)
    return Decimal(nums[-1]) if nums else None


def parse_amount(text: str):
    m = re.search(r"(?:中标金额|成交金额)：?(\d+(?:\.\d+)?)元", text)
    return Decimal(m.group(1)) if m else None


def classify(text: str):
    if "螺纹钢" in text: return "螺纹钢", "steel"
    if "重废" in text: return "重废", "scrap"
    if "废钢" in text: return "废钢", "scrap"
    return "盘扣式脚手架租赁" if "盘扣" in text else "脚手架租赁", "scaffold"


def detect_city(text: str):
    for city in ["北京", "天津", "呼和浩特", "乌兰察布", "深圳", "广州", "佛山"]:
        if city in text: return city
    return None


def detect_region(text: str):
    city = detect_city(text)
    if city in ["北京", "天津"]: return "华北"
    if city in ["呼和浩特", "乌兰察布"]: return "内蒙古"
    if city in ["深圳", "广州", "佛山"]: return "华南"
    return "全国"


def detect_unit(text: str):
    if "元/吨/天" in text: return "元/吨/天"
    if "元/㎡" in text or "元/平方米" in text: return "元/㎡"
    return "元/吨"


def detect_spec(text: str):
    m = re.search(r"(HRB400E\s*\d+mm|\d+mm以上|48系)", text)
    return m.group(1) if m else None


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]

if __name__ == "__main__":
    asyncio.run(main())
