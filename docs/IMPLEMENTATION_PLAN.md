# 全站实施计划（P0–P6）

> 基于 `docs/00_README.md`、`docs/01_common.md` 与 `docs/02–08` 通读后的计划。  
> **尚未写业务代码**；确认后再从 P0 开始。每阶段完成后按对应页面验收清单自查并停下来等确认。

---

## (1) 分阶段实施计划

### P0｜外壳 + 公共组件 + 7 页样例静态还原

**目标**：路由、tokens、公共组件齐套；7 页用样例 JSON 对齐设计稿；390px 无横向溢出。

| 动作 | 主要文件 |
|---|---|
| 迁入新文档 | 新增 `docs/00_README.md`～`08_sources.md`；更新 `docs/design/*-mockup.dc.html`；保留 bloomberg 图；归档或删除旧 `CURSOR_PROMPT_consensus.md`（避免双源） |
| 配置骨架 | 新增 `config/watchlist.yaml`、`config/sources.yaml`、`config/ai.yaml`、`config/red_rules.yaml`、`config/analysts.yaml`；扩展 `config/companies/MU.yaml`（按 01 §7.1） |
| 样例数据 | 新增 `web/public/sample/{watchlist,review,financials,call,consensus,price,sources}.json`（结构=正式 `data/pages/...`） |
| 样式 | 改 `web/src/styles/tokens.css`（补全 01 §4.1 新 token）；新增 `base.css` |
| 公共组件 | 整理/新增：`AppHeader`、`StockHeader`、`StockTabs`、`Segmented`、`ToggleChip`、`KpiCard`、`DataTable`、`Placeholder`、`Tag`、`Banner`、`FooterNote`（现有 header/stockHeader/segmented 迁入并补齐） |
| 路由 | 改 `web/src/router.ts`、`main.ts`：`#/`、`#/MU`、`#/MU/review/<FQ>`、`#/MU/financials`、`#/MU/call[/<FQ>]`、`#/MU/consensus`、`#/MU/price`、`#/sources` |
| 七页前端 | 新增 `web/src/pages/{watchlist,review,financials,call,price,sources}/`；**重构**现有 `pages/consensus/` 以复用公共组件 |
| 验收 | 逐页对照设计稿列差异表；390px 自查 |

---

### P1｜财务报表 + StockHeader 真数

**目标**：XBRL → `financials`；StockHeader 接真实股价/市值等。

| 动作 | 主要文件 |
|---|---|
| 库 | 扩展 `scripts/lib/fiscal.py`（以 10-Q/10-K `fp/fy/end` 为准）；新增 `http.py`、`edgar.py` |
| 诊断 | 新增 `scripts/diagnose_xbrl_tags.py` → `data/raw/MU/xbrl_tags.txt`；回填 `MU.yaml` 的 `xbrl_map` |
| 抓取/构建 | 新增 `fetch_financials.py`、`build_page_financials.py`；复用/强化 `fetch_prices.py` |
| 数据 | `data/financials/MU.json`、`data/pages/MU/financials.json`；`data/prices/MU.json` |
| 前端 | `pages/financials/*` 切到正式 JSON；StockHeader 读公共 header 数据 |
| 工作流 | 扩展 `data.yml` |
| 测试 | pytest：累计相减、FY23 n.m.、环比禁用规则 |

---

### P2｜分析师预期真管道 + 观察池 NTM/修正/FPE 列

**目标**：每日共识快照尽早开跑；共识页接真数；观察池表格相关列可用。

| 动作 | 主要文件 |
|---|---|
| 复用并校准 | `fetch_consensus.py`、`fetch_secondary.py`、`fetch_actuals.py`、`build_history.py`、`build_page_consensus.py` |
| 对齐 01 | 增速/颜色尽量在 Python 产出显示串与 `up/down/flat/na`（Forward PE 输入仍可前端算） |
| 数据 | `data/snapshots/MU/`、`actuals/`、`history/`、`pages/MU/consensus.json` |
| 观察池部分 | `build_page_watchlist.py` 先出 NTM / 修正30D / Forward PE（其余列可仍为占位） |
| 前端 | consensus 切正式数据；watchlist 表先接这几列 |

---

### P3｜股价反应 + 财报解读数字部分

**目标**：事件快照、价格反应页；解读页数字卡/拆解/指引（无 AI 文案）。

| 动作 | 主要文件 |
|---|---|
| 工作流 | 新增 `.github/workflows/earnings-night.yml` |
| 抓取 | `fetch_press.py`、`parse_press.py`、`fetch_events_snapshot.py`（盘后价/IV） |
| 构建 | `build_page_price.py`、`build_page_review.py`（数字块） |
| 数据 | `data/raw/.../press.html`、`data/releases/`、`data/events/MU.json`、`pages/MU/price.json`、`pages/MU/review/<FQ>.json` |
| 前端 | price 全页；review 的总结数字行、6 卡、拆解、指引表 |
| 依赖 | `pandas_market_calendars`（交易日） |

---

### P4｜电话会 + 财报解读 AI（手动模式）

**目标**：跑通「任务包 → Cursor 处理 → ai_check → 页面显示」一整轮。

| 动作 | 主要文件 |
|---|---|
| AI 基建 | `config/ai.yaml`；`scripts/lib/ai.py`；`ai_prepare.py`、`ai_check.py`；`scripts/prompts/*_vN.md`；目录 `ai/tasks/`、`ai/outputs/` |
| 电话会 | `fetch_remarks.py`、`fetch_transcript.py`、`build_page_call.py`；`data/calls/`、`pages/MU/call-*.json`、`call-index.json` |
| 解读 AI | review 的 summary/why/struct note/talk；`config/notes/MU.yaml` |
| 前端 | call 页（含 minisearch）；review AI 区「待生成」状态 |
| 工作流 | `data.yml` 生成任务包 + 开 Issue |

---

### P5｜观察池完整功能

**目标**：公告、红色规则、日历 .ics、最近发布、待验证跟踪项。

| 动作 | 主要文件 |
|---|---|
| 抓取 | `fetch_filings.py`（8-K/Form4）、评级可选 |
| 规则 | `config/red_rules.yaml`；`build_filings.py` |
| 构建 | 完善 `build_page_watchlist.py`；生成 `data/pages/calendar.ics` |
| 前端 | watchlist KPI/公告/日历/最近发布；列选择 localStorage |

---

### P6｜数据说明 + 运维告警

**目标**：sources 页由 YAML+_status 驱动；失败可观测。

| 动作 | 主要文件 |
|---|---|
| 配置 | 完善 `config/sources.yaml` |
| 构建 | `build_sources.py` → `data/pages/sources.json` |
| 前端 | sources 页接真状态 |
| 运维 | `_status` 写入规范；可选失败自动开 Issue；核对 cron/permissions |

---

## (2) 现有代码：可复用 vs 需调整

### 可复用（保留演进）

- **共识页图表与交互**：`trendChart` / `revisionChart` / `history` / `forwardPe` / `gridTable` / `detailTable` —— 逻辑与设计稿对齐，P0 抽公共组件后继续用。
- **管道雏形**：`fetch_consensus` / `actuals` / `prices` / `secondary`、`build_history` / `build_page_consensus`、`lib/fiscal|fmt|io`、pytest/vitest、`data.yml`+`pages.yml`、`data/pages/MU/consensus.json` 样例。
- **视觉方向**：`tokens.css`、深色顶栏、Segmented、est-bg 语义 —— 按 01 补 token 即可。

### 需要调整（不要另起炉灶）

| 项 | 现状 | 目标 |
|---|---|---|
| 路由 | `#/MU/overview` 等占位 | `#/MU`=解读；`financials/call/price/review/<FQ>` |
| 组件边界 | 页内私有表格/样式多 | 抽出 `DataTable`/`KpiCard`/`Tag`/`Placeholder`/`StockTabs` |
| 口径位置 | 前端算 YoY/颜色 | 01：Python 出显示串+色类；仅 PE 输入例外（P0 可暂留前端算，P1/P2 收拢） |
| `MU.yaml` | 旧字段 | 对齐 01 骨架（`fy_label`、`xbrl_map`、`metrics`、`executives`…） |
| tokens | 缺 placeholder/alert/tag/ok-mid-bad 等 | 按 01 §4.1 补全 |
| 文档 | 仅旧 consensus prompt | 换 00–08 + 全套 design mockup |
| Pages 构建 | 拷贝整个 `data/` | 至少保证 `data/pages`（可继续拷全量 `data`） |
| 多股票 | 逻辑偏 MU | watchlist 8 只；`has_page` 控制可点进 |

---

## (3) 矛盾 / 不清楚 / 实现风险

### 需拍板或澄清

1. **颜色由谁算**：01 要求后端给 `up/down/…`；02 §5 又写「后端或前端统一函数二选一」。建议：**全站后端给色类**；符号着色仅作展示兜底。
2. **百分比精度**：01 默认 ≥1000% 取整、否则 1 位；06 四宫格例外全取整。将按页执行；跨页同一数字（如解读卡环比 `+30.8%` vs 共识表）允许不同精度。
3. **n.m. 定义**：01「当期 < 0 且基数 > 0（符号翻转）」比 06 旧文更严。建议以 **01 为准**，并改 consensus 测试。
4. **08 `remarks.missing`「用第三方文字稿顶替」** vs 01「不默默换源」。建议：原文 tab 可标明来源切换；**不把第三方当官方准备稿静默填入**。
5. **02「复用已有美港股公告抓取」**：本仓库无该任务。P5 是新建 EDGAR 抓取，还是对接外部仓库？
6. **06 引用不存在的 `CURSOR_PROMPT_site.md`**：视为笔误，以 `01_common.md` 为准。
7. **SEC User-Agent 邮箱**：01 要求真实联系邮箱——用哪个？
8. **GitHub「添加股票」链接**：owner/repo 写死 `cool1990/stock_investing_dashboard`，还是构建时注入？

### 实现风险（高）

- **第三方文字稿 / Nasdaq / MarketBeat**：反爬、改版；必须失败隔离。
- **盘后价与期权 IV**：yfinance 分钟线/期权链窗口短，强依赖 `earnings-night.yml` 当晚快照；历史只能「近似/不可得」。
- **新闻稿 HTML 表解析 + 数字反查**：MU 表结构一变即碎；P3 要强审计字段。
- **XBRL tag 漂移与重述**：P1 诊断脚本是硬前置；累计相减失败必须留空。
- **电话会 AI 回填量**：FQ1-22 起约 20 场，手动模式工作量大——P4 先打通最新 1 场，历史分批。
- **版权**：05 要求原文 tab 以官方/准备稿为主；第三方只作校对片段。
- **P0 工作量**：7 页静态还原 + 公共组件重构，比「只做共识」大一个数量级；建议 P0 以「结构+主交互+样例」对齐设计稿，细枝末节列入差异表留到各页真数据阶段打磨。

---

## 推进约定

1. 确认本计划（并尽量回复上面 1–8 的偏好）后，从 **P0** 开始。
2. 每完成一个阶段：按对应页面文档的「验收清单」逐项自查并汇报，**停下来等确认**后再进入下一阶段。
3. 数字诚实：缺数据用占位符，不编造、不插值、不用其他来源默默顶替。
4. AI 默认手动模式：脚本生成任务包，Cursor 处理；DeepSeek 只保留接口。
