
BOT_NAME = "price_crawler"
SPIDER_MODULES = ["price_crawler.spiders"]
NEWSPIDER_MODULE = "price_crawler.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 15
RETRY_ENABLED = True
RETRY_TIMES = 3
COOKIES_ENABLED = False
LOG_LEVEL = "INFO"
DUPEFILTER_CLASS = "scrapy.dupefilters.RFPDupeFilter"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"

DOWNLOADER_MIDDLEWARES = {
    "price_crawler.middlewares.RandomUserAgentMiddleware": 400,
}
ITEM_PIPELINES = {
    "price_crawler.pipelines.DatabasePipeline": 300,
}

# Compliance: public pages only. No login, no CAPTCHA bypass, no paid data.
