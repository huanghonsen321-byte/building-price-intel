# 全国资料库 / 数据源库

管理全国脚手架、盘扣、模板脚手架、周转材料、钢材、废钢、
招投标公告、价格行情、附件解析、人工导入和授权数据源的长效资料库。

## 配置文件

| 文件 | 说明 |
|------|------|
| `app/crawlers/config/source_library_national.json` | 全国资料源注册表 |
| `app/crawlers/config/keyword_library.json` | 关键词分类库 |

## 资料库规模

| 分类 | 数量 |
|------|------|
| 国家级源 | 7 |
| 广东省级源 | 5 |
| 广东地市源 | 21 |
| 全国省份源 | 30 |
| 价格源 | 10 |
| 手动/授权源 | 3 |
| **总计** | **76** |

## 字段说明

每个资料源包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 数据源名称 |
| url | str | 公开页面 URL |
| domain | str | 域名 |
| source_level | enum | national/province/city/enterprise/industry/price/manual/authorized |
| source_type | enum | bid/price/attachment/search/mixed |
| acquisition_method | enum | 采集方法（见下表） |
| parser_name | str|null | 关联的爬虫 parser 类名 |
| enabled | bool | 是否加入 V4 runner |
| parser_status | enum | not_started/fixture_ready/parser_ready/blocked/needs_browser/deprecated |
| requires_browser | bool | 是否需要 Playwright |
| keywords | list | 关联关键词 |
| province | str|null | 省份 |
| city | str|null | 城市 |
| tags | list | 标签 |
| notes | str | 备注 |

### 采集方法

| 方法 | 说明 |
|------|------|
| national_aggregate_search | 国家级聚合搜索 |
| official_search_page | 官方搜索页 |
| public_api | 公开 API |
| html_list_page | HTML 列表页解析 |
| browser_discovery | 浏览器发现 |
| attachment_parse | 附件解析 |
| search_api_discovery | 搜索 API 发现 |
| manual_import | 手动导入 |
| authorized_api | 授权 API |

## 如何新增数据源

1. 编辑 `app/crawlers/config/source_library_national.json`
2. 在对应分类下添加条目
3. 设置 `enabled: false` 和 `parser_status: "not_started"`
4. 运行验证：

```bash
curl http://127.0.0.1:9000/api/source-library/validate?name=新源名称
```

## 如何验证数据源

```bash
# API 验证（不绕 403/验证码/登录）
curl -X POST "http://127.0.0.1:9000/api/source-library/validate?name=广东省公共资源交易平台"
```

## 如何写 parser

1. `parser_status` 从 `not_started` 开始
2. 获取公开页面 fixture → `fixture_ready`
3. 在 `app/crawlers/real_public_sources.py` 添加 parser 类
4. 注册到 `crawl_service.py` 的 `BID_CRAWLER_REGISTRY`
5. 编写单元测试
6. 更新 `parser_status` → `parser_ready`
7. 在 `source_library_national.json` 填写 `parser_name`

## 如何处理 blocked

| blocked_reason | 处理方式 |
|----------------|----------|
| blocked_403 | 记录 blocker_reason，暂停该源 |
| captcha_required | 记录，不绕过，不保存 cookie |
| login_required | 记录，可尝试 --manual-login |
| paid_content | 记录，跳过 |

被 blocked 的源设置 `parser_status: "blocked"`，`enabled: false`。

## API

```
GET  /api/source-library              列表（支持 province/city/source_level/source_type/parser_status/enabled 过滤）
GET  /api/source-library/stats        统计
GET  /api/source-library/{id}         单个源详情（name 或 1-based index）
POST /api/source-library/validate     验证 URL（不绕限制）
POST /api/source-library/import       从 JSON 导入
POST /api/source-library/{id}/enable  启用
POST /api/source-library/{id}/disable 禁用
```

## V4 Runner 接入

```bash
# 默认模式（sources_national_v4.json）
./scripts/run_national_public_crawl_v4.sh --dry-run --province 广东 --max-sources 10

# 资料库模式（source_library_national.json）
./scripts/run_national_public_crawl_v4.sh --dry-run --source-library --province 广东 --max-sources 10

# 其他过滤
./scripts/run_national_public_crawl_v4.sh --source-library --source-level national --max-sources 5
./scripts/run_national_public_crawl_v4.sh --source-library --source-type bid --parser-status parser_ready
```

## Dashboard

`GET /api/crawl/dashboard` 包含 `source_library_stats`：

```json
{
  "total_sources": 76,
  "enabled_sources": 9,
  "parser_ready_sources": 8,
  "national_sources": 68,
  "guangdong_sources": 26,
  "price_source_count": 13,
  ...
  "by_parser_status": {"not_started": 61, "parser_ready": 8, "blocked": 1, ...}
}
```

## 测试

```bash
pytest tests/test_source_library.py -v  # 25 tests
```

覆盖：
- 资料库加载
- 关键词库加载
- 国家级源存在
- 广东 21 地市源存在
- 31 省份源存在
- 价格源存在
- 查询过滤（province/city/source_level/enabled/parser_status）
- Schema 验证
- 可靠性评分
- 不含代理池/绕过逻辑
