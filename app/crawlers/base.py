from dataclasses import dataclass
from datetime import date


SUPPORTED_KEYWORDS = ["脚手架", "盘扣", "扣件式脚手架", "钢管脚手架", "模板脚手架", "爬架", "周转材料租赁"]


@dataclass(frozen=True)
class RawBidDocument:
    source_name: str
    source_url: str
    title: str
    publish_date: date | None
    region: str | None
    html_content: str | None
    text_content: str


class PublicBidCrawler:
    source_name = "base"

    def search(self, keyword: str) -> list[RawBidDocument]:
        raise NotImplementedError
