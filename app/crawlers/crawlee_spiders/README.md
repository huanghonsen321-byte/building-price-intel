# Crawlee Python spiders

Install:

```bash
pip install crawlee
```

Run a public page crawl and write normalized records to the backend database:

```bash
cd app/crawlers/crawlee_spiders
DATABASE_URL=sqlite+pysqlite:///../../../local_test.db \
python run_crawlee.py --start-url "https://example.com/steel-prices" --output-db "../output.db"
```

JS rendering:

```bash
python run_crawlee.py --start-url "https://example.com/js-page" --render-js
```

Compliance:

- Public pages only.
- No login.
- No CAPTCHA bypass.
- No paid data.
- Random 1-3 second delay before requests.
- Retries are handled by Crawlee PlaywrightCrawler when `--render-js` is available, otherwise by httpx/outer scheduler.
