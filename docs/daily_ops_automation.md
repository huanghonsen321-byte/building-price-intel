# 日常数据抓取、AI行情摘要与企业微信提醒运维说明

## 本机部署状态

- 后端服务：user systemd `building-price-intel.service`
- 监听地址：`http://127.0.0.1:9000`
- 工作目录：`/home/huanghonsen/building-price-intel`
- 持久 SQLite：`/home/huanghonsen/building-price-intel/local_prod.db`
- 环境文件：`/home/huanghonsen/building-price-intel/.env`（已被 `.gitignore` 忽略）

## 后端服务命令

```bash
systemctl --user status building-price-intel.service
systemctl --user restart building-price-intel.service
journalctl --user -u building-price-intel.service -n 100 --no-pager
curl http://127.0.0.1:9000/api/health
```

## 手动运行日常流水线

```bash
cd /home/huanghonsen/building-price-intel
./scripts/run_daily_ops.sh --no-vllm --json
./scripts/print_price_summary.sh
```

流水线内容：

1. `alembic upgrade head`
2. 如果价格表为空，自动写入 seed baseline，保证行情摘要可用
3. 对 `DAILY_CRAWL_KEYWORDS` 逐个运行公开数据采集；单个关键词失败时按 `DAILY_CRAWL_RETRY_ATTEMPTS` 重试，使用 `DAILY_CRAWL_RETRY_BACKOFF_SECONDS` 递增退避
4. 对 pending raw bid documents 执行 AI 抽取；`--no-vllm` 时使用离线规则 fallback
5. 生成今日行情中文摘要
6. 发送每日早报
7. 对本轮新增公告按关键词/地区/金额阈值发送重要公告提醒

## Hermes Cron 定时任务

当前创建了两个 Hermes cron job：

- `building-price-intel 每日抓取+AI摘要+企业微信提醒`
  - schedule: `0 8 * * *`
  - script: `~/.hermes/scripts/building_price_daily_ops.sh`
  - 作用：每天 08:00 跑完整流水线
- `building-price-intel 健康巡检`
  - schedule: `0 */6 * * *`
  - script: `~/.hermes/scripts/building_price_healthcheck.sh`
  - 作用：每 6 小时检查后端健康和行情摘要；健康失败时尝试重启 user service

查看/管理：

```bash
hermes cron list
hermes cron run <job_id>
hermes cron pause <job_id>
hermes cron resume <job_id>
```

## 企业微信 webhook 配置

`.env` 中保留：

```bash
WECOM_WEBHOOK_URL=
```

如果为空，流水线使用 `mock` sender：会写入 notification_logs 并把 cron 输出发回 Hermes 当前会话，但不会真实发企业微信。

配置真实企业微信机器人：

```bash
cd /home/huanghonsen/building-price-intel
python - <<'PY'
from pathlib import Path
path = Path('.env')
text = path.read_text()
url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=替换成你的key'
lines = []
seen = False
for line in text.splitlines():
    if line.startswith('WECOM_WEBHOOK_URL='):
        lines.append(f'WECOM_WEBHOOK_URL={url}')
        seen = True
    else:
        lines.append(line)
if not seen:
    lines.append(f'WECOM_WEBHOOK_URL={url}')
path.write_text('\n'.join(lines) + '\n')
PY
systemctl --user restart building-price-intel.service
./scripts/run_daily_ops.sh --no-vllm --json
```

不要把真实 webhook/token 提交到 Git。

## 验收命令

```bash
curl http://127.0.0.1:9000/api/health
curl -X POST http://127.0.0.1:9000/api/crawl/run \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"脚手架","source_type":"public"}'
curl http://127.0.0.1:9000/api/prices/today/summary
curl 'http://127.0.0.1:9000/api/notifications/logs?page=1&page_size=10'
```

## 下一轮 Flutter UI/UX 与数据可视化迭代规划

### 1. 首页业务驾驶舱

- 今日价格摘要卡：钢材、废钢、脚手架三类分组展示
- 异常波动卡：突出涨跌超过阈值的地区/品类
- 最新重要公告卡：按金额、地区、关键词排序
- 数据新鲜度提示：最后采集时间、最近成功任务、失败任务数

### 2. 行情趋势可视化

- 多品种对比折线：螺纹钢、废钢、盘扣租赁价同图
- 日期范围切换：7/30/90 天
- 涨跌颜色：上涨红/下跌绿/持平灰
- tooltip 显示：日期、价格、涨跌、来源

### 3. 中标案例地图/地区分布

- 按省市统计公告数量和金额
- 广东、华北、内蒙古优先
- 支持点击地区进入案例列表

### 4. 报价页二期

- 保存报价单到本地历史
- 一键复制报价文本
- 导出图片/PDF 报价单
- 报价参数模板：租赁、包工包料、吨日计费

### 5. 数据质量与复核页

- 低置信度 AI 抽取 review_tasks 列表
- 缺失字段高亮
- 原文 evidence snippets 对照
- 人工修正后更新结构化案例

建议优先级：

1. 首页业务驾驶舱
2. 行情趋势多品种对比
3. 报价单保存/复制/导出
4. 低置信度复核页
5. 地区分布/地图
