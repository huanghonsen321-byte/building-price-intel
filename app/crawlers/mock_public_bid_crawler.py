from datetime import date

from app.crawlers.base import PublicBidCrawler, RawBidDocument, SUPPORTED_KEYWORDS


class MockPublicBidCrawler(PublicBidCrawler):
    source_name = "Mock公共资源交易中心"
    base_url = "https://mock-public-bid.local"

    def search(self, keyword: str) -> list[RawBidDocument]:
        if keyword not in SUPPORTED_KEYWORDS and not any(item in keyword for item in SUPPORTED_KEYWORDS):
            return []
        return [
            RawBidDocument(
                source_name=self.source_name,
                source_url=f"{self.base_url}/notice/pankou-2026-001",
                title="乌兰察布产业园盘扣式脚手架租赁服务中标公告",
                publish_date=date(2026, 5, 12),
                region="内蒙古",
                html_content="<p>乌兰察布产业园盘扣式脚手架租赁服务中标公告</p>",
                text_content=(
                    "乌兰察布产业园盘扣式脚手架租赁服务中标公告。采购人：中建北方工程有限公司。"
                    "中标人：内蒙古周转材料租赁有限公司。中标金额：1800000元。"
                    "服务范围：盘扣式脚手架租赁、搭拆及运输。工程量：脚手架面积30000平方米。"
                    "服务期：180天。发布时间：2026-05-12。"
                ),
            ),
            RawBidDocument(
                source_name=self.source_name,
                source_url=f"{self.base_url}/notice/steelpipe-2026-002",
                title="呼和浩特医院项目钢管脚手架专业分包成交结果公告",
                publish_date=date(2026, 5, 10),
                region="内蒙古",
                html_content="<p>呼和浩特医院项目钢管脚手架专业分包成交结果公告</p>",
                text_content=(
                    "呼和浩特医院项目钢管脚手架专业分包成交结果公告。采购人：北疆建设集团。"
                    "代理机构：内蒙古工程招标代理有限公司。成交单位：呼市安建脚手架工程有限公司。"
                    "成交金额：960000元。服务内容：扣件式钢管脚手架搭设、维护和拆除。租期：6个月。"
                    "发布时间：2026-05-10。"
                ),
            ),
        ]
