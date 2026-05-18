# Crawlab configuration

This directory contains optional Crawlab deployment files for scheduling the project crawler scripts.

Crawlab is optional because the current no-sudo local environment does not provide Docker. If Docker is available:

```bash
docker run -d -p 8000:8000 --name crawlab \
  --restart always \
  crawlab/crawlab:latest
```

Suggested script paths inside this repository:

- Scrapy: `app/crawlers/scrapy_spiders/price_crawler`
- Crawlee: `app/crawlers/crawlee_spiders/run_crawlee.py`
- pyspider: `app/crawlers/pyspider/config.json`

Compliance defaults:

- Public pages only.
- No login.
- No CAPTCHA bypass.
- No paid data.
- Random delays and retries enabled in each crawler framework.
