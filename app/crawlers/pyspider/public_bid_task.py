#!/usr/bin/env python
# pyspider task template for public bid pages.
# NOTE: pyspider 0.3.10 uses the reserved keyword `async` and is not directly
# runnable on Python 3.14. Keep this task as a deployment template for older
# Python runtimes/containers, or run through Crawlab with a compatible image.

from pyspider.libs.base_handler import *


class Handler(BaseHandler):
    crawl_config = {
        "headers": {"User-Agent": "building-price-intel/0.1 public crawler"},
        "timeout": 20,
        "retries": 3,
    }

    @every(minutes=24 * 60)
    def on_start(self):
        self.crawl("http://search.ccgp.gov.cn/bxsearch?searchtype=1&kw=%E8%84%9A%E6%89%8B%E6%9E%B6", callback=self.index_page)

    @config(age=10 * 24 * 60 * 60)
    def index_page(self, response):
        for each in response.doc("a").items():
            title = each.text()
            if "脚手架" in title or "盘扣" in title:
                self.crawl(each.attr.href, callback=self.detail_page)

    @config(priority=2)
    def detail_page(self, response):
        return {
            "record_type": "bid",
            "source_name": "pyspider公开公告源",
            "source_url": response.url,
            "title": response.doc("title").text(),
            "text_content": response.doc("body").text(),
        }
