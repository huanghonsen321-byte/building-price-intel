# Attachment Extractor

从公告 HTML 中自动发现附件链接，下载并解析 PDF / DOCX / XLSX / HTML 文件，
提取文本内容进入 AI / rule-based extraction 上下文。

## 支持的文件类型

| 类型 | 解析库 | 说明 |
|------|--------|------|
| PDF | pypdf | 提取页面文字 |
| DOCX | python-docx | 提取段落 + 表格 |
| XLSX | openpyxl | 提取所有 sheet 的单元格 |
| HTML | BeautifulSoup | 去除 script/style 后提取文本 |

## 安全约束

- 默认文件大小限制：20 MB
- 不执行宏、不运行附件内的代码
- 下载失败记录 error_message，不崩溃 pipeline
- 本地缓存到 `/tmp/building-price-intel/attachments/`（可通过 `ATTACHMENT_CACHE_DIR` 覆盖）

## 附件发现

在公告 HTML 中扫描 `<a>` 标签：

- 匹配文件扩展名：`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`
- 匹配关键词：附件、下载、招标文件、中标结果、采购合同、工程量清单、报价清单
- URL 自动解析为绝对地址

## 数据库

表：`bid_attachments`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| raw_document_id | FK → bid_raw_documents | 所属公告 |
| source_url | Text | 公告 URL |
| file_url | Text | 附件 URL |
| file_name | String(512) | 文件名 |
| file_type | String(32) | pdf/docx/xlsx/html |
| file_size | Integer | 文件大小 |
| local_path | Text | 本地缓存路径 |
| extracted_text | Text | 解析文本 |
| parse_status | String(32) | pending/download_failed/parsed/parse_failed |
| error_message | Text | 错误信息 |

## 与采集流水线集成

`run_public_crawl` 保存 `bid_raw_documents` 后自动：

1. 发现附件 → 写入 `bid_attachments`
2. 下载附件 → 提取文本
3. 附件文本合并到 AI extraction 输入
4. 增强抽取中标金额、面积、租期、单价等字段
5. 低置信度自动进入 `review_tasks`

## API

```
GET  /api/attachments                    列表（支持 parse_status / file_type 过滤）
GET  /api/attachments/{id}               单个附件详情
POST /api/attachments/parse-pending      触发批量解析 pending 附件
```

## 增强抽取字段

附件文本中优先提取：

- 中标金额（普通数字 / 万 / 亿）
- 建筑面积 / 脚手架面积（平方米 / ㎡ / m2）
- 吨位
- 租期（天 / 月）
- 单价（元/㎡, 元/吨/天, 元/月, 元/吨）
- 采购人 / 中标人 / 代理机构

## 运行

```bash
# 小批量 dry-run
./scripts/run_national_public_crawl_v4.sh --dry-run --max-keywords 3 --max-sources 3

# 小批量运行（不发送企业微信）
./scripts/run_national_public_crawl_v4.sh --run --no-wecom --max-keywords 3 --max-sources 3

# 手动触发附件解析
curl -X POST http://localhost:8012/api/attachments/parse-pending?limit=50
```

## 当前限制

- 附件下载依赖真实网络访问
- 加密 PDF 不可解析
- 扫描件 PDF 无 OCR
- .doc（旧版 Word）尝试当 .docx 解析，可能失败
