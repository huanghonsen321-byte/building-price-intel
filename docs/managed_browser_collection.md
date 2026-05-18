# Managed Browser Collection

合规托管浏览器采集：使用普通 Playwright 在 allowlist 域名范围内采集公开页面，
自动搜索公告、下载附件、提取文本并入库。

## 合规边界

| 行为 | 允许 | 禁止 |
|------|------|------|
| 访问公开页面 | 仅 allowlist 域名 | 非 allowlist 域名 |
| 绕过 403/验证码/登录/付费墙 | 否 | 是 |
| 保存 cookie/token/session | 否 | 是 |
| 使用代理池 | 否 | 是 |
| stealth/fingerprint bypass | 否 | 是 |
| 提交浏览器 profile | 否 | 是 |

遇到 403 / captcha / login_required / paid_content 立即停止该源，
记录 blocked_reason，不继续绕过。

## Allowlist

配置文件：`app/crawlers/config/browser_allowlist.json`

初始允许域名：
- ggzy.gov.cn
- ccgp.gov.cn
- zycg.gov.cn
- ygp.gdzwfw.gov.cn
- gdgpo.czt.gd.gov.cn
- gzggzy.cn / ywtb.gzggzy.cn
- szggzy.com
- foshan.gov.cn
- dg.gov.cn

## 运行模式

### 1. dry-run（默认安全）

```bash
python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --dry-run
python scripts/run_managed_browser_collect.py --source gzggzy --keyword 盘扣 --dry-run
python scripts/run_managed_browser_collect.py --source ggzy --keyword 钢管 --dry-run
```

不联网、不写库、不推送企业微信，只打印将访问的 source/keyword/allowlist/预计动作。

### 2. run（headless 自动采集）

```bash
# 基础采集
python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架

# 附带下载附件
python scripts/run_managed_browser_collect.py --source gzggzy --keyword 盘扣 --download-attachments

# 显示浏览器窗口
python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --no-headless

# 限制数量
python scripts/run_managed_browser_collect.py --source ygp --keyword 钢管 --max-results 10

# JSON 输出
python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --json
```

### 3. manual-login（手动登录后采集）

```bash
python scripts/run_managed_browser_collect.py --source ygp --keyword 脚手架 --manual-login
```

打开可见浏览器窗口，等待手动登录/确认后，在 allowlist 域名内继续采集。
不读取、不打印、不保存 cookie/token。

## 支持的数据源

| source key | 名称 | 策略 |
|------------|------|------|
| ggzy | 全国公共资源交易平台 | 首页列表解析 |
| ccgp | 中国政府采购网 | 搜索表单 |
| zycg | 中央政府采购网 | SPA 导航 |
| ygp | 广东省公共资源交易平台 | SPA 导航 |
| gdgpo | 广东政府采购智慧云平台 | SPA 导航 |
| gzggzy | 广州公共资源交易平台 | HTML 页面 |

## 审计日志

表：`managed_browser_runs`

```sql
id, source_name, keyword, mode, started_at, ended_at,
visited_urls (JSON), downloaded_files (JSON),
records_created, attachments_created,
blocked_reason, error_message, created_at
```

API：
```
GET  /api/managed-browser/runs
GET  /api/managed-browser/runs/{id}
```

## 采集流程

1. 加载 allowlist 配置
2. 验证 source key 和域名
3. 启动 Playwright（fresh context，无 cookie）
4. 导航到搜索页
5. 检测 blocked 指标（403/captcha/login/paid）
6. 执行搜索策略（表单填写 / SPA 导航 / 首页解析）
7. 提取公告链接（关键词过滤）
8. 逐个打开公告详情页
9. 保存 bid_raw_documents
10. 可选：发现并下载附件 → attachment_extractor
11. 写入 managed_browser_runs 审计记录

## Blocked 原因

| blocked_reason | 触发条件 |
|----------------|----------|
| domain_not_allowed | URL 不在 allowlist 中 |
| blocked_403 | HTTP 403 / 本文含 403 标记 |
| captcha_required | 验证码 / 人机验证 |
| login_required | 需要输入密码 / 登录 |
| paid_content | 付费 / 会员 / VIP |

## 接入新的广东源

1. 在 `browser_allowlist.json` 添加域名到 `allowlist`
2. 在 `source_mappings` 添加 source key、URL、search_strategy
3. dry-run 测试
4. 如果 site 需要登录，用 `--manual-login` 首次采集
5. 编写 parser 单元测试

## 当前限制

- Playwright 需要手动安装：`playwright install chromium`
- SPA 页面搜索策略待实际调试优化
- 附件下载依赖真实网络
- manual-login 需要交互式终端
