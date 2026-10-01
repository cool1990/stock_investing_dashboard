# 财报台 · 个股财报分析

静态站点，部署在 GitHub Pages。首页是观察池；个股页覆盖财报解读、财务报表、电话会、分析师预期、股价反应，另有数据说明页。浏览器只读同源 JSON，不直接请求第三方 API。

**第一只完整实现的股票是 MU（美光）**；其余股票先出现在观察池。

## 本地运行

```bash
# 前端（P0 读 web/public/sample/*.json）
cd web
npm install
npm run dev          # http://127.0.0.1:43123/stock_investing_dashboard/
```

```bash
# Python 数据管道
cp .env.example .env   # 填入 SEC_USER_AGENT（本地用）
python3 -m pip install -r requirements.txt
python3 scripts/fetch_consensus.py --ticker MU
python3 scripts/fetch_actuals.py --ticker MU
python3 scripts/fetch_prices.py --ticker MU
python3 scripts/build_history.py --ticker MU
python3 scripts/build_page_consensus.py --ticker MU
```

`SEC_USER_AGENT` 示例值：`stock_investing_dashboard raycao2023@gmail.com`  
GitHub Actions：Settings → Variables → `SEC_USER_AGENT`（Variable，不是 Secret）。

## 测试

```bash
pytest
cd web && npm test
```

## 部署

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
2. push 到 `main` 触发 `pages.yml`。
3. `data.yml` 工作日定时抓取共识/实际/股价；共识按**绝对财期名**（如 `FQ1-27`）写入 `data/snapshots/`。可在 Actions 里手动 Run workflow。

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
