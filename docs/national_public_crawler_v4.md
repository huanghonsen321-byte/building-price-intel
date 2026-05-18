# Hermes V4 合规限速全国公开数据采集说明

用户原始目标是“全国省市 + 广东各地 + 国家级 + 行业协会 + 钢材/废钢/脚手架/建筑材料”的自动采集、增量去重、AI 抽取和企业微信推送。

本仓库实现的是合规限速版：

- 只使用公开页面/公开接口。
- 不绕过登录、验证码、付费墙。
- 不使用代理池规避站点限制。
- 不做无限并发、不做无限循环。
- 不在生产脚本里 `pip install` 或 `playwright install`。
- 不直接写 SQLite 原始表，统一走现有 `scripts/run_daily_ops.sh`、服务层去重、AI/rule fallback、企业微信推送链路。

## 配置文件

`app/crawlers/config/sources_national_v4.json`

里面包含：

- enabled=true 的已接入公开源：
  - 生意社公开价格页
  - 中国政府采购网
- enabled=false 的候选源：
  - 广东省公共资源交易平台
  - 全国公共资源交易平台
  - 钢材之家公开行情
  - 再生资源网公开行情
  - 央企采购公开公告

候选源要在确认公开页面结构、robots/站点规则和字段映射后逐个接入。

## 运行 dry-run

```bash
cd /home/huanghonsen/building-price-intel
./scripts/run_national_public_crawl_v4.sh --dry-run
```

Dry-run 不联网、不写库、不推送企业微信，只验证配置、关键词选择和输出报告。

## 真实运行

```bash
cd /home/huanghonsen/building-price-intel
./scripts/run_national_public_crawl_v4.sh --run --max-keywords 8
```

默认使用 `--no-vllm` 离线规则 fallback，避免本地 vLLM 未启动时阻塞。如果要使用 vLLM：

```bash
./scripts/run_national_public_crawl_v4.sh --run --use-vllm --max-keywords 8
```

## 输出

报告写入：

`app/crawlers/output/national_v4_YYYYMMDD_HHMMSS.json`

## 环境变量

可通过 `.env` 或命令行覆盖：

```bash
DAILY_CRAWL_RETRY_ATTEMPTS=3
DAILY_CRAWL_RETRY_BACKOFF_SECONDS=2
DAILY_BRIEFING_REGIONS=广东,华北,内蒙古,全国
DAILY_BRIEFING_CATEGORIES=steel,scrap,scaffold
BID_ALERT_KEYWORDS=脚手架,盘扣,租赁,钢管,周转材料
BID_ALERT_REGIONS=广东,广州,深圳,佛山,内蒙古,华北,全国
```

## 后续新增公开源流程

1. 先在 `sources_national_v4.json` 增加候选源，`enabled=false`。
2. 用小样本页面编写 parser 单元测试。
3. 确认不需要登录/验证码/付费数据。
4. 将源切换为 `enabled=true`。
5. 跑：

```bash
pytest -q
./scripts/run_national_public_crawl_v4.sh --dry-run
./scripts/run_national_public_crawl_v4.sh --run --max-keywords 2
```

6. PR 说明中附来源、字段映射、限速策略和验收输出。
