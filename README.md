# 财报台 · 个股分析师预期（MU 首发）

静态站点：在 GitHub Pages 上展示美股「分析师预期」——未来共识、90 天修正轨迹、历史超预期。浏览器只读同源 JSON，不直接请求第三方 API。

## 本地运行

```bash
# 前端
cd web
npm install
npm run dev          # http://127.0.0.1:43123/stock_investing_dashboard/
```

打开后默认进入 `#/MU/consensus`。

```bash
# Python 数据管道
python -m pip install -r requirements.txt
python scripts/fetch_consensus.py --ticker MU
python scripts/fetch_actuals.py --ticker MU
python scripts/fetch_prices.py --ticker MU
python scripts/build_history.py --ticker MU
python scripts/build_page_consensus.py --ticker MU
```

## 测试

```bash
pytest
cd web && npm test
```

## 部署

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
2. push 到 `main` 触发 `pages.yml`：构建 Vite（`base: /stock_investing_dashboard/`）并部署。
3. `data.yml` 工作日定时抓取共识/实际/股价；仅在有变更时由 `github-actions[bot]` 提交。

线上地址：`https://cool1990.github.io/stock_investing_dashboard/`

## 目录

- `web/` — Vite + TypeScript 前端（原生 DOM，手写 SVG）
- `config/companies/MU.yaml` — 财年、指引、覆盖
- `data/pages/MU/consensus.json` — 页面聚合数据（前端唯一数据源）
- `scripts/` — 抓取与聚合
- `docs/CURSOR_PROMPT_consensus.md` — 完整产品/设计说明

## 设计原则

- 缺失数据一律显示 `[ ]`，禁止编造或插值
- 蓝 = 上调 / 好于预期，橙 = 下调 / 差于预期（不用红绿）
- 数字用 IBM Plex Mono，正文用 Noto Sans SC
