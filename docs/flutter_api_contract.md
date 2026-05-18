# Flutter API Contract

## Base URLs

- Android 模拟器访问电脑本机后端：`http://10.0.2.2:9000`
- 本机浏览器访问后端：`http://127.0.0.1:9000`
- Android 真机调试访问电脑后端：使用电脑局域网 IP，例如 `http://192.168.x.x:9000`

> 后端已允许本机 Web 调试 CORS 来源：`http://localhost:3000`、`http://127.0.0.1:3000`、`http://localhost:5173`、`http://127.0.0.1:5173`。

## 通用分页返回

以下列表接口统一返回：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

Dart 建议：

```dart
class PageResult<T> {
  final List<T> items;
  final int total;
  final int page;
  final int pageSize;
}
```

## GET `/api/health`

返回字段：

- `status`: 服务状态，正常为 `ok`
- `service`: 服务名

## GET `/api/prices`

参数：

- `category`: 价格分类，例如 `steel`、`scrap`、`scaffold`
- `region`: 区域，例如 `华北`
- `city`: 城市，例如 `北京`
- `product_name`: 产品名模糊搜索，例如 `螺纹钢`
- `date_from`: 起始日期，`YYYY-MM-DD`
- `date_to`: 结束日期，`YYYY-MM-DD`
- `page`: 页码，默认 `1`
- `page_size`: 每页条数，默认 `20`，最大 `100`

`items` 返回字段：

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
- `updated_at`
- `created_at`

Dart model 建议字段：

```dart
class PriceDaily {
  final int id;
  final DateTime date;
  final String category;
  final String region;
  final String? city;
  final String productName;
  final String? spec;
  final String? material;
  final String unit;
  final double price;
  final double? changeValue;
  final bool taxIncluded;
  final String sourceName;
  final String? sourceUrl;
}
```

## GET `/api/prices/today`

返回最新日期的价格数组，字段同 `PriceDaily`。该接口不分页。

## GET `/api/prices/trends`

参数：

- `category`: 默认 `steel`
- `product_name`: 产品名精确筛选
- `days`: 天数，默认 `30`，范围 `1-365`

返回数组字段：

- `date`
- `price`
- `product_name`
- `region`
- `city`
- `unit`

## GET `/api/scaffold/bids`

参数：

- `keyword`: 项目名、采购人、中标人、服务范围模糊搜索
- `province`: 省份
- `city`: 城市
- `scaffold_type`: 脚手架类型，例如 `盘扣`
- `procurement_type`: 采购类型，例如 `租赁`
- `review_status`: 复核状态，例如 `pending`、`approved`、`rejected`
- `date_from`: 公告起始日期，`YYYY-MM-DD`
- `date_to`: 公告结束日期，`YYYY-MM-DD`
- `page`: 页码，默认 `1`
- `page_size`: 每页条数，默认 `20`，最大 `100`

`items` 返回字段：

- `id`
- `raw_document_id`
- `project_name`
- `province`
- `city`
- `district`
- `buyer`
- `agency`
- `winner`
- `bid_amount`
- `announcement_type`
- `scaffold_type`
- `procurement_type`
- `service_scope`
- `duration_text`
- `quantity_text`
- `area_m2`
- `tonnage`
- `rental_days`
- `pricing_method`
- `source_url`
- `publish_date`
- `ai_summary`
- `extraction_confidence`
- `review_status`
- `created_at`
- `updated_at`

Dart model 建议字段：

```dart
class ScaffoldBidCase {
  final int id;
  final String projectName;
  final String? province;
  final String? city;
  final String? buyer;
  final String? winner;
  final double? bidAmount;
  final String? scaffoldType;
  final String? procurementType;
  final double? areaM2;
  final double? tonnage;
  final int? rentalDays;
  final String sourceUrl;
  final DateTime? publishDate;
  final String reviewStatus;
}
```

## GET `/api/scaffold/bids/{case_id}`

返回单个脚手架招投标案例，字段同 `ScaffoldBidCase`，并包含：

- `price_references`: 参考价数组，字段见下方 `ScaffoldPriceReference`

## GET `/api/scaffold/prices/reference`

参数：

- `region`: 地区或城市，例如 `呼和浩特`
- `scaffold_type`: 脚手架类型，例如 `盘扣`
- `calculated_unit`: 折算单位，例如 `元/㎡`、`元/吨/天`、`元/月`
- `confidence`: 置信度，例如 `high`、`medium`、`low`
- `page`: 页码，默认 `1`
- `page_size`: 每页条数，默认 `20`，最大 `100`

`items` 返回字段：

- `id`
- `bid_case_id`
- `price_type`
- `scaffold_type`
- `region`
- `calculated_unit`
- `calculated_price`
- `formula`
- `confidence`
- `notes`
- `created_at`

Dart model 建议字段：

```dart
class ScaffoldPriceReference {
  final int id;
  final int bidCaseId;
  final String priceType;
  final String? scaffoldType;
  final String? region;
  final String calculatedUnit;
  final double calculatedPrice;
  final String formula;
  final String confidence;
  final String? notes;
}
```

## POST `/api/quote/scaffold/calculate`

请求字段：

- `scaffold_type`: 脚手架类型，默认 `盘扣`
- `region`: 地区，可选
- `area_m2`: 面积，单位 `㎡`，当参考单位为 `元/㎡` 时需要
- `rental_days`: 租赁天数，当参考单位为 `元/吨/天` 时需要
- `rental_months`: 租赁月数，当参考单位为 `元/月` 时需要
- `tonnage`: 吨数，当参考单位为 `元/吨/天` 时需要

返回字段：

- `scaffold_type`
- `region`
- `calculated_unit`
- `reference_price`
- `estimated_amount`: 估算金额；缺少必要参数时为 `null`
- `confidence`
- `formula`: 计算公式或缺少字段说明
- `reference_count`

Dart model 建议字段：

```dart
class ScaffoldQuoteResult {
  final String scaffoldType;
  final String? region;
  final String calculatedUnit;
  final double referencePrice;
  final double? estimatedAmount;
  final String confidence;
  final String formula;
  final int referenceCount;
}
```
