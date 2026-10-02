# 财报台 · 个股财报分析

静态站点，部署在 GitHub Pages。首页是观察池；个股页覆盖财报解读、财务报表、电话会、分析师预期、股价反应，另有数据说明页。浏览器只读同源 JSON，不直接请求第三方 API。

**第一只完整实现的股票是 MU（美光）**；其余股票先出现在观察池。

## 本地运行

```bash
# 前端
cd web
npm install
npm run dev          # http://127.0.0.1:43123/stock_investing_dashboard/
```

页面只读 `data/pages/`。没有生成数据时显示加载错误，不会把 MU 样例套到其他代码上。开发服务器会优先读仓库根目录的 `data/`。

```bash
# Python 数据管道
cp .env.example .env   # 填入 SEC_USER_AGENT（本地用）
python3 -m pip install -r requirements.txt

# P1：XBRL 财务报表 + 股价页头
python3 scripts/diagnose_xbrl_tags.py --ticker MU
python3 scripts/fetch_financials.py --ticker MU
python3 scripts/fetch_prices.py --ticker MU
python3 scripts/build_page_financials.py --ticker MU
python3 scripts/build_page_header.py --ticker MU

# 共识（P0/P2）
python3 scripts/fetch_consensus.py --ticker MU
python3 scripts/fetch_actuals.py --ticker MU
python3 scripts/build_history.py --ticker MU
python3 scripts/build_page_consensus.py --ticker MU
```

`SEC_USER_AGENT` 示例值：`stock_investing_dashboard raycao2023@gmail.com`  
GitHub Actions：Settings → Variables → `SEC_USER_AGENT`（Variable，不是 Secret）。

## 测试

```bash
python3 -m pytest
cd web && npm test
```

## 部署

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
2. push 到 `main` 触发 `pages.yml`。
3. `data.yml` 工作日刷新观察池里的全部股票，并把 `data/` 与 `web/public/data/` 一起提交。共识只写入 `data/snapshots/<T>/YYYY-MM-DD.json`。
4. `pages.yml` 除了 push 到 `main`，还会在「Daily data refresh」或「Earnings night snapshot」成功后部署。`GITHUB_TOKEN` 的 push 不会再触发 Pages，所以不能只靠 push 事件。
5. 仓库变量 `SEC_USER_AGENT`（Settings → Secrets and variables → Actions → Variables，不是 Secret）必须设成带联系方式的字符串，例如 README 里的本地示例。云端代理如果要抓 SEC，把同一个值放进 Cursor 的环境密钥，不要写进仓库。

线上：`https://cool1990.github.io/stock_investing_dashboard/`

## 路由

| Hash | 页面 |
|---|---|
| `#/` | 观察池 |
| `#/MU` / `#/MU/review` | 财报解读 |
| `#/MU/financials` | 财务报表 |
| `#/MU/call` | 电话会 |
| `#/MU/consensus` | 分析师预期 |
| `#/MU/price` | 股价反应 |
| `#/sources` | 数据说明 |

## 目录

- `docs/00`–`08` — 唯一需求来源（见 `docs/IMPLEMENTATION_PLAN.md`）
- `web/` — Vite + TypeScript（原生 DOM，手写 SVG）
- `web/public/sample/` — P0 样例 JSON
- `config/` — watchlist / companies / sources / ai / red_rules / analysts
- `data/` — 管道产物（snapshots、pages…）
- `scripts/` — 抓取与聚合
- `ai/` — 手动模式 AI 任务包（P4）

## 设计原则

- 缺失显示 `[ ]` /「未获取」，禁止编造或静默用第三方顶替官方准备稿
- 色类由后端给出（`up` / `down` / `flat` / `na`）；蓝=上调/超预期，橙=下调/低于预期
- 数字用 IBM Plex Mono，正文用 Noto Sans SC

## 管道阶段（P0–P6）

| 阶段 | 内容 |
|---|---|
| P0 | 七页外壳 + 样例 |
| P1 | XBRL 财务报表 + StockHeader 真数 |
| P2 | 共识快照刷新 + 观察池 NTM / 修正30D / Forward PE |
| P3 | 股价反应（次日/T+5）+ 解读数字卡 |
| P4 | 电话会 / 解读 AI 手动任务包（`ai_prepare` → Cursor → `ai_check --apply`） |
| P5 | EDGAR 公告 + 红色规则 + `calendar.ics` |
| P6 | 数据说明页由 `sources.yaml` + `_status.json` 驱动 |

