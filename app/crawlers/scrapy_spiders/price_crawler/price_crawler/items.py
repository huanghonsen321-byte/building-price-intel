
import scrapy


class StandardCrawlerItem(scrapy.Item):
    record_type = scrapy.Field()
    source_name = scrapy.Field()
    source_url = scrapy.Field()
    crawl_time = scrapy.Field()
    publish_time = scrapy.Field()
    category = scrapy.Field()
    type = scrapy.Field()
    region = scrapy.Field()
    city = scrapy.Field()
    product_name = scrapy.Field()
    specification = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    amount = scrapy.Field()
    title = scrapy.Field()
    text_content = scrapy.Field()
    html_content = scrapy.Field()
    extra = scrapy.Field()
