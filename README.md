# building-price-intel

FastAPI + PostgreSQL/SQLite + SQLAlchemy/Alembic 后端 MVP，用于建筑钢材、废钢、脚手架价格与脚手架招投标案例的采集、AI 抽取、折算和报价参考。

## 快速开始：SQLite 开发模式

SQLite 适合本机开发、Flutter Android 模拟器联调和 CI smoke test。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

DATABASE_URL=sqlite+pysqlite:///./local_dev.db alembic upgrade head
DATABASE_URL=sqlite+pysqlite:///./local_dev.db python -m app.seed.seed_data
DATABASE_URL=sqlite+pysqlite:///./local_dev.db uvicorn app.main:app --reload --host 127.0.0.1 --port 9000
```

也可以直接使用脚本或 Makefile：

```bash
./scripts/run_sqlite_dev.sh
make dev
```

## PostgreSQL 正式模式

PostgreSQL 适合持续运行、多人共用和正式部署。

```bash
docker compose up -d postgres
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+psycopg://building_price:building_price@127.0.0.1:5432/building_price_intel
alembic upgrade head
python -m app.seed.seed_data
uvicorn app.main:app --host 0.0.0.0 --port 9000
```

## Makefile 用法

```bash
make install   # 安装 Python 依赖
make migrate   # 执行 alembic upgrade head，使用当前 DATABASE_URL
make seed      # 写入 mock/seed 数据，使用当前 DATABASE_URL
make dev       # SQLite 开发模式：迁移、种子、启动 uvicorn :9000
make test      # pytest -q
make api-test  # 对正在运行的后端执行 curl smoke test
make clean     # 清理本地 SQLite DB 和 Python 缓存
```

## 开发脚本

```bash
./scripts/check_env.sh      # 检查 Python/Alembic/数据库/vLLM 配置
./scripts/seed_sqlite.sh    # 迁移并写入 SQLite seed 数据
./scripts/run_sqlite_dev.sh # SQLite + uvicorn 开发服务
./scripts/test_api.sh       # curl 检查 health/list/quote API
```

## API 示例

列表接口统一返回：

```json
{"items": [], "total": 0, "page": 1, "page_size": 20}
```

常用 curl：

```bash
curl http://127.0.0.1:9000/api/health
curl 'http://127.0.0.1:9000/api/prices?category=steel&page=1&page_size=5'
curl 'http://127.0.0.1:9000/api/prices?region=华北&city=北京&product_name=螺纹钢&date_from=2026-05-01&date_to=2026-05-18'
curl http://127.0.0.1:9000/api/prices/today
curl 'http://127.0.0.1:9000/api/prices/trends?category=steel&days=7'

curl 'http://127.0.0.1:9000/api/scaffold/bids?keyword=脚手架&province=内蒙古&scaffold_type=盘扣&page=1&page_size=10'
curl 'http://127.0.0.1:9000/api/scaffold/prices/reference?region=呼和浩特&calculated_unit=元/㎡&confidence=medium'

curl -X POST http://127.0.0.1:9000/api/quote/scaffold/calculate \
  -H 'Content-Type: application/json' \
  -d '{"scaffold_type":"盘扣","region":"呼和浩特","area_m2":1000,"rental_days":90,"tonnage":20}'

# mock 发送一次每日行情早报，并写入 notification_logs
curl -X POST 'http://127.0.0.1:9000/api/notifications/daily-briefing/send?channel=mock&target=mock://local'
curl 'http://127.0.0.1:9000/api/notifications/logs?page=1&page_size=10'
```


## Flutter 调试地址

- Android 模拟器访问电脑本机后端：`http://10.0.2.2:9000`
- 本机浏览器访问后端：`http://127.0.0.1:9000`
- Android 真机调试访问电脑后端：使用电脑局域网 IP，例如 `http://192.168.x.x:9000`

后端 CORS 已允许本机 Web 调试来源：`http://localhost:3000`、`http://127.0.0.1:3000`、`http://localhost:5173`、`http://127.0.0.1:5173`。

### Flutter UI 验收步骤

```bash
cd mobile/flutter_app
flutter analyze
flutter test
flutter run -d <android-emulator-id> --dart-define=API_BASE_URL=http://10.0.2.2:9000
```

移动端中标案例页已改为底部筛选面板，支持清空筛选、下拉刷新、按 `items/total/page/page_size` 加载更多。点击中标案例卡片可进入详情页查看项目、地区、采购人、中标人、金额、面积、吨位、租期、AI 摘要和来源链接。

## vLLM / aeon-local AI 抽取

配置项：

- `VLLM_BASE_URL`: 默认 `http://127.0.0.1:8000/v1`
- `VLLM_MODEL`: 默认 `aeon-local`

启动本地 OpenAI-compatible vLLM 服务后，后端会调用 `/chat/completions` 做脚手架公告字段抽取。例如：

```bash
export VLLM_BASE_URL=http://127.0.0.1:8000/v1
export VLLM_MODEL=aeon-local
uvicorn app.main:app --host 127.0.0.1 --port 9000
```

如果 vLLM 离线、超时或返回 JSON 解析失败，`app/ai/extractor.py` 会记录日志并返回低置信度 fallback JSON，不会让 FastAPI 后端崩溃。

## 公开数据源与合规边界

当前爬虫模块已移除，后续将重新设计和实现。

合规边界：

- 不登录、不绕验证码、不抓付费数据。
- 请求间隔随机，支持重试和异常日志。
- 保存 `source_name`、`source_url`、`crawl_time`、`publish_time`、原文、任务状态和结构化结果，方便人工复核。
- 不同单位、地区、规格、含税状态分字段保存，不强行合并口径。

## 配置

复制 `.env.example` 为 `.env` 后可调整：

- `DATABASE_URL`: 默认 `postgresql+psycopg://building_price:building_price@127.0.0.1:5432/building_price_intel`
- `VLLM_BASE_URL`: 默认 `http://127.0.0.1:8000/v1`
- `VLLM_MODEL`: 默认 `aeon-local`
- `WECOM_WEBHOOK_URL`: 企业微信机器人 webhook。不要提交真实 token；本地和 CI 可用 `channel=mock` 验证发送链路。

## 企业微信 / 微信提醒

当前支持两类提醒：

- 每日行情早报：价格行情、近期公告、数据来源说明。
- 重要公告提醒：关键词、地区、金额阈值命中后生成提醒。

本地 mock 验证：

```bash
DATABASE_URL=sqlite+pysqlite:///./local_dev.db python scripts/send_daily_briefing.py
curl -X POST 'http://127.0.0.1:9000/api/notifications/daily-briefing/send?channel=mock&target=mock://local'
curl 'http://127.0.0.1:9000/api/notifications/logs'
```

企业微信机器人发送时使用 `channel=wecom_webhook`，`target` 传入运行环境中的 webhook URL。生产环境应通过环境变量/密钥管理注入 webhook，仓库只保留 `.env.example` 占位。

## 目录结构

```text
app/
  main.py
  core/        # config/database
  models/      # SQLAlchemy ORM 表
  schemas/     # Pydantic v2 输出/输入模型
  api/         # FastAPI routers
  services/    # 价格、案例、报价、折算业务逻辑

  ai/          # 本地 vLLM 字段抽取
  tasks/       # APScheduler 占位
  seed/        # mock/seed 数据
alembic/       # Alembic 迁移
scripts/       # SQLite/dev/API smoke test 脚本
docs/          # Flutter API 契约
```

## 测试

验收命令：

```bash
DATABASE_URL=sqlite+pysqlite:///./local_test.db alembic upgrade head
DATABASE_URL=sqlite+pysqlite:///./local_test.db python -m app.seed.seed_data
DATABASE_URL=sqlite+pysqlite:///./local_test.db pytest -q
```
