# building-price-intel

FastAPI + PostgreSQL + SQLAlchemy/Alembic 后端 MVP，用于建筑钢材、废钢、脚手架价格与脚手架招投标案例的采集、AI 抽取、折算和报价参考。

## 本地验收命令

```bash
cd building-price-intel

docker compose up -d postgres

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
python -m app.seed.seed_data

uvicorn app.main:app --reload --host 127.0.0.1 --port 9000
```

## curl 验收

```bash
curl http://127.0.0.1:9000/api/health
curl http://127.0.0.1:9000/api/prices/today
curl http://127.0.0.1:9000/api/scaffold/bids
curl http://127.0.0.1:9000/api/scaffold/prices/reference
```

更多接口：

```bash
curl 'http://127.0.0.1:9000/api/prices?category=steel'
curl 'http://127.0.0.1:9000/api/prices/trends?category=steel&days=7'

curl -X POST http://127.0.0.1:9000/api/crawl/run \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"脚手架"}'

curl http://127.0.0.1:9000/api/crawl/tasks

curl -X POST http://127.0.0.1:9000/api/quote/scaffold/calculate \
  -H 'Content-Type: application/json' \
  -d '{"scaffold_type":"盘扣","region":"呼和浩特","area_m2":1000,"rental_days":90}'
```

## 配置

复制 `.env.example` 为 `.env` 后可调整：

- `DATABASE_URL`: 默认 `postgresql+psycopg://building_price:building_price@127.0.0.1:5432/building_price_intel`
- `VLLM_BASE_URL`: 默认 `http://127.0.0.1:8000/v1`
- `VLLM_MODEL`: 默认 `aeon-local`

AI 抽取模块位于 `app/ai/extractor.py`，通过 OpenAI-compatible `/chat/completions` 调用本地 vLLM。vLLM 不在线时返回低置信度结构化结果，不影响 mock 爬虫运行。

## 目录结构

```text
app/
  main.py
  core/        # config/database
  models/      # SQLAlchemy ORM 表
  schemas/     # Pydantic v2 输出/输入模型
  api/         # FastAPI routers
  services/    # 价格、案例、报价、折算业务逻辑
  crawlers/    # 合规 mock crawler 框架
  ai/          # 本地 vLLM 字段抽取
  tasks/       # APScheduler 占位
  seed/        # mock/seed 数据
alembic/       # Alembic 迁移
```

## 测试

```bash
source .venv/bin/activate
pytest
```

如果当前机器没有 Docker，也可以用 SQLite 做代码级 smoke test：

```bash
DATABASE_URL=sqlite+pysqlite:///./local_test.db alembic upgrade head
DATABASE_URL=sqlite+pysqlite:///./local_test.db python -m app.seed.seed_data
DATABASE_URL=sqlite+pysqlite:///./local_test.db pytest -q
```
