# Flutter API Contract

本文档记录当前后端 FastAPI 路由、Flutter `ApiClient` 已封装接口、Dart model 对应关系和移动端解析注意事项。

审计时间：2026-05-19
分支：`test/app-backend-api-contract-audit`

## Base URL

- Android 模拟器访问电脑本机后端：`http://10.0.2.2:9000`
- 本机调试 / 桌面浏览器：`http://127.0.0.1:9000`
- Android 真机调试：使用电脑局域网 IP，例如 `http://192.168.x.x:9000`

Flutter 默认逻辑：

- Android 非 Web：`http://10.0.2.2:9000`
- 其他平台：`http://127.0.0.1:9000`
- 可通过 `--dart-define=API_BASE_URL=http://<host>:9000` 覆盖。

## 通用约定

### 分页格式

大部分列表接口返回：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

Flutter 对应：`PageResult<T>`。

特殊情况：

- `GET /api/source-library` 后端返回 `items/total/limit/offset`，Flutter `ApiClient.sourceLibrary()` 会转换为 `PageResult<SourceLibraryItem>`。
- `GET /api/notifications/logs` 返回 `items/total/page/page_size`。

### Query 参数

中文 query 参数必须使用 Dio `queryParameters` 或 `Uri` 编码，不要手拼 URL。

示例：

```dart
await dio.get('/api/scaffold/bids', queryParameters: {
  'province': '广东',
  'review_status': 'pending',
  'page': 1,
  'page_size': 20,
});
```

### Error state

后端不可用、接口 4xx/5xx 或网络超时时，Flutter 页面应通过 `LoadState` 显示 error state，并允许刷新重试。

### Local-only / auth 注意

当前 APP 面向本地工作站和受信任局域网调试。`/api/crawl/*`、`/api/source-library/*`、`/api/attachments/*`、`/api/managed-browser/*`、`/api/notifications/*` 属于运维/内部接口，当前后端没有登录鉴权；不要直接暴露到公网。若未来部署到公网或多人使用，需要先增加认证、权限和敏感字段脱敏。

### duplicate skipped 语义

自动采集结果中：

- `total_found > 0`
- `total_saved == 0`

通常表示发现了公告，但正式库已有相同 URL，被去重跳过，不一定是失败。Flutter model 使用 `CrawlRun.hasDuplicateSkippedSignal` 标记该状态；该 getter 还要求 `status != 'failed'` 且 `error_message == null`，避免把失败 run 误判为去重。

## Flutter 已用 / 已封装接口

| 功能 | Method | Path | ApiClient 方法 | Dart model |
|---|---:|---|---|---|
| 健康检查 | GET | `/api/health` | `health()` | `HealthStatus` |
| 今日价格 | GET | `/api/prices/today` | `todayPrices()` | `List<PriceDaily>` |
| 今日价格摘要 | GET | `/api/prices/today/summary` | `todaySummary()` | `TodayPriceSummary` |
| 价格列表 | GET | `/api/prices` | `prices()` | `PageResult<PriceDaily>` |
| 价格趋势 | GET | `/api/prices/trends` | `trends()` | `List<PriceTrendPoint>` |
| 脚手架案例 | GET | `/api/scaffold/bids` | `scaffoldBids()` | `PageResult<ScaffoldBidCase>` |
| 案例复核 | POST | `/api/scaffold/bids/{case_id}/review` | `reviewBidCase()` | void |
| 参考价 | GET | `/api/scaffold/prices/reference` | `scaffoldReferences()` | `PageResult<ScaffoldPriceReference>` |
| 脚手架报价 | POST | `/api/quote/scaffold/calculate` | `calculateQuote()` | `ScaffoldQuoteResult` |
| 采集 Dashboard | GET | `/api/crawl/dashboard` | `crawlDashboard()` | `CrawlDashboardSummary` |
| 自动爬虫健康 | GET | `/api/crawl-orchestrator/health` | `crawlOrchestratorHealth()` | `CrawlOrchestratorHealth` |
| 自动爬虫失败源 | GET | `/api/crawl-orchestrator/failures` | `crawlOrchestratorFailures()` | `List<CrawlRunSource>` |
| 自动爬虫历史 | GET | `/api/crawl-orchestrator/runs` | `crawlOrchestratorRuns()` | `PageResult<CrawlRun>` |
| 自动爬虫详情 | GET | `/api/crawl-orchestrator/runs/{id}` | `crawlOrchestratorRunDetail()` | `CrawlRunDetail` |
| 自动爬虫最新 | GET | `/api/crawl-orchestrator/latest` | `crawlOrchestratorLatest()` | `CrawlRunDetail` |
| 资料库统计 | GET | `/api/source-library/stats` | `sourceLibraryStats()` | `SourceLibraryStats` |
| 资料库列表 | GET | `/api/source-library` | `sourceLibrary()` | `PageResult<SourceLibraryItem>` |
| 附件列表 | GET | `/api/attachments` | `attachments()` | `PageResult<Attachment>` |
| 托管浏览器运行 | GET | `/api/managed-browser/runs` | `managedBrowserRuns()` | `PageResult<ManagedBrowserRun>` |
| 通知日志 | GET | `/api/notifications/logs` | `notificationLogs()` | `PageResult<NotificationLog>` |

当前未封装且 APP 未调用：

- `GET /api/scaffold/bids/{case_id}`
- `POST /api/scaffold/bids/extract-pending`
- `POST /api/crawl/run`
- `GET /api/crawl/tasks`
- `POST /api/crawl-orchestrator/run`
- `GET /api/source-library/{source_id}`
- `POST /api/source-library/validate`
- `POST /api/source-library/import`
- `POST /api/source-library/{source_id}/enable`
- `POST /api/source-library/{source_id}/disable`
- `GET /api/attachments/{attachment_id}`
- `POST /api/attachments/parse-pending`
- `GET /api/managed-browser/runs/{run_id}`
- `POST /api/notifications/daily-briefing/send`

当前不存在且 Flutter 不应调用：

- `GET /api/pricing/regional-prices`

## 接口详情

### GET `/api/health`

响应：

```json
{"status":"ok","service":"building-price-intel"}
```

Model：`HealthStatus`

字段：`status`, `service`。

### GET `/api/prices/today`

响应：`PriceDaily[]`。

`PriceDaily` 字段：

- `id`
- `date`
- `category`
- `region`
- `city`
- `product_name`
- `spec`
- `material`
- `unit`
- `price`
- `change_value`
- `tax_included`
- `source_name`
- `source_url`

### GET `/api/prices/today/summary`

响应示例：

```json
{
  "date": "2026-05-19",
  "total_records": 12,
  "summary_text": "今日价格样本 12 条",
  "regions": {"广东": {"count": 5}},
  "anomalies": [],
  "updated_at": "2026-05-19T12:00:00"
}
```

Model：`TodayPriceSummary`

字段：`date`, `total_records`, `summary_text`, `regions`, `anomalies`, `updated_at`。

### GET `/api/prices`

参数：

- `category`
- `region`
- `city`
- `product_name`
- `page`
- `page_size`

响应：`PageResult<PriceDaily>`。

### GET `/api/prices/trends`

参数：

- `category`，默认 `steel`
- `product_name`
- `days`

响应：`PriceTrendPoint[]`。

字段：`date`, `price`, `product_name`, `region`, `city`, `unit`。

### GET `/api/scaffold/bids`

参数：

- `keyword`
- `province`
- `city`
- `scaffold_type`
- `procurement_type`
- `review_status`
- `page`
- `page_size`

响应：`PageResult<ScaffoldBidCase>`。

`ScaffoldBidCase` 字段：

- `id`
- `project_name`
- `province`
- `city`
- `buyer`
- `winner`
- `bid_amount`
- `scaffold_type`
- `procurement_type`
- `area_m2`
- `tonnage`
- `rental_days`
- `source_url`
- `publish_date`
- `review_status`
- `service_scope`
- `ai_summary`
- `missing_fields`
- `raw_evidence_snippets`
- `extraction_confidence`

请求示例：

```bash
curl -sS --get http://127.0.0.1:9000/api/scaffold/bids \
  --data-urlencode 'province=广东' \
  --data 'review_status=pending' \
  --data 'page=1' \
  --data 'page_size=20'
```

### POST `/api/scaffold/bids/{case_id}/review`

请求：

```json
{"status":"approved","reviewer_note":"字段已确认"}
```

Flutter：`reviewBidCase()`。

### GET `/api/scaffold/prices/reference`

参数：

- `region`
- `scaffold_type`
- `calculated_unit`
- `confidence`
- `page`
- `page_size`

响应：`PageResult<ScaffoldPriceReference>`。

字段：`id`, `bid_case_id`, `price_type`, `scaffold_type`, `region`, `calculated_unit`, `calculated_price`, `formula`, `confidence`, `notes`。

### POST `/api/quote/scaffold/calculate`

请求示例：

```json
{
  "scaffold_type": "盘扣",
  "region": "广东",
  "pricing_method": "area",
  "area_m2": 1000,
  "rental_days": 30,
  "setup_dismantle_fee": 3000,
  "transport_fee": 1000
}
```

响应：`ScaffoldQuoteResult`。

字段：

- `scaffold_type`
- `region`
- `pricing_method`
- `calculated_unit`
- `reference_price`
- `estimated_amount`
- `unit_area_price`
- `unit_ton_day_price`
- `cost_breakdown`
- `confidence`
- `formula`
- `reference_count`

### GET `/api/crawl/dashboard`

响应：`CrawlDashboardSummary`。

字段：

- `blocked_source_count`
- `blocked_reason_distribution`
- `available_source_count`
- `today_successful_source_count`
- `guangdong_success_rate`
- `national_success_rate`
- `source_library_stats`

### GET `/api/crawl-orchestrator/health`

响应：`CrawlOrchestratorHealth`。

字段：`total_runs`, `latest_run`, `latest_status`。

### GET `/api/crawl-orchestrator/latest`

响应：`CrawlRunDetail`。

```json
{
  "run": {
    "id": 8,
    "run_type": "guangdong",
    "status": "partial_success",
    "total_sources": 3,
    "total_found": 8,
    "total_saved": 0
  },
  "sources": []
}
```

如果没有任何历史 run，后端当前返回 404；Flutter 首页对该接口使用 error fallback，不阻断首页其它数据。

### GET `/api/crawl-orchestrator/runs`

响应：`PageResult<CrawlRun>`。

### GET `/api/crawl-orchestrator/runs/{id}`

响应：`CrawlRunDetail`。

### GET `/api/crawl-orchestrator/failures`

响应：`CrawlRunSource[]`。

### GET `/api/source-library/stats`

响应：`SourceLibraryStats`。

字段：

- `total_sources`
- `enabled_sources`
- `parser_ready_sources`
- `blocked_sources`
- `national_sources`
- `guangdong_sources`
- `province_source_count`
- `city_source_count`
- `price_source_count`
- `attachment_source_count`
- `manual_import_sources`
- `authorized_api_sources`
- `by_acquisition_method`
- `by_parser_status`

### GET `/api/source-library`

参数：`province`, `source_level`, `source_type`, `parser_status`, `enabled`, `limit`, `offset`。

后端响应：`items/total/limit/offset`。
Flutter 转换为：`PageResult<SourceLibraryItem>`。

### GET `/api/attachments`

参数：`parse_status`, `file_type`, `page`, `page_size`。

响应：`PageResult<Attachment>`。

### GET `/api/managed-browser/runs`

参数：`source_name`, `keyword`, `blocked_reason`, `page`, `page_size`。

响应：`PageResult<ManagedBrowserRun>`。

### GET `/api/notifications/logs`

参数：`page`, `page_size`。

后端响应字段：`items`, `total`, `page`, `page_size`。

响应 item：`NotificationLog`。

## Dart model 安全解析要求

当前 `models.dart` 已按以下规则解析：

- snake_case 后端字段映射为 camelCase Dart 字段。
- `int/double/string/null` 数字安全解析。
- 日期字段使用 `DateTime.tryParse`，无效日期返回 `null`。
- 缺字段不抛异常，使用空字符串、0、null 或 `[]` fallback。
- 列表字段缺失时默认 `[]`。
- 字典计数字段通过 `Map<String, int>` 安全转换。

## Contract 测试

后端：`tests/test_app_backend_api_contract.py`

覆盖：

- Flutter API client 中所有路径都存在于 FastAPI routes。
- 用户关心的 APP 后端路由完整存在。
- `/api/crawl-orchestrator/latest` 返回 Flutter 需要字段。
- `/api/source-library/stats` 返回 Flutter 需要字段。
- `/api/crawl/dashboard` 返回 Flutter 需要字段。
- `/api/prices/today/summary` 返回 Flutter 需要字段。
- `/api/scaffold/bids?review_status=pending&page=1&page_size=20` 返回分页结构。
- `/api/pricing/regional-prices` 当前不存在且 Flutter 不调用。
- `/api/notifications/logs`、`/api/managed-browser/runs` 返回 APP 可解析结构。

Flutter：`mobile/flutter_app/test/api_model_contract_test.dart`

覆盖：

- `CrawlRun.fromJson`
- `CrawlRunSource.fromJson`
- `SourceLibraryStats.fromJson`
- `TodayPriceSummary.fromJson`
- `ScaffoldBidCase.fromJson`
- `RegionalPriceItem.fromJson`
- duplicate skipped 状态模型解析
- `CrawlDashboardSummary`, `Attachment`, `NotificationLog`, `ManagedBrowserRun` 缺字段/null 字段安全解析。
