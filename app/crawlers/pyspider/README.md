# pyspider deployment

Install:

```bash
pip install pyspider
```

Configured files:

- `config.json` — local SQLite task/project/result DB config.
- `public_bid_task.py` — public bid task template.

Run command requested by the deployment plan:

```bash
cd app/crawlers/pyspider
pyspider -c config.json
```

Important environment note:

`pyspider==0.3.10` currently fails under Python 3.14 because its CLI imports code using the reserved keyword `async`. The package installs, but `pyspider --help` raises a SyntaxError. Use one of these options for actual pyspider Web UI deployment:

1. Run pyspider in a Python 3.6/3.7 compatible container.
2. Use Crawlab to schedule the template in a compatible image.
3. Prefer Scrapy/Crawlee for the local Python 3.14 environment.

Compliance remains the same: public pages only; no login; no CAPTCHA bypass; no paid data.
