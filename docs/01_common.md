# 01 全站通用规格

本文件规定所有页面共用的约定。各页面文件只写本页特有的内容，与本文件冲突时以页面文件为准。

---

## 1. 项目背景

这是一个**个股财报分析网站**。每只股票都要回答四个问题：
1. 这次财报好不好；
2. 为什么；
3. 市场原本预期什么；
4. 接下来该盯什么。

核心数据有三类：财报文件、电话会、分析师预期。首页是观察池，用来横向比较多只股票、汇总重要公告。

**初始股票池（8 只）**：

| 代码 | 名称 | 分组 | 细分 |
|---|---|---|---|
| MU | Micron | AI 硬件 | 存储 |
| NVDA | NVIDIA | AI 硬件 | AI 芯片 |
| AVGO | Broadcom | AI 硬件 | AI 芯片 / 网络 |
| SNDK | SanDisk | AI 硬件 | 存储 |
| CRWV | CoreWeave | AI 硬件 | AI 云 |
| CDNS | Cadence | 软件 | EDA 软件 |
| NOW | ServiceNow | 软件 | 企业软件 |
| UBER | Uber | 平台 | 出行平台 |

**第一只完整实现的股票是 MU**，其他 7 只先只出现在观察池里，个股页留到以后逐只接入。

## 2. 硬约束

1. **部署**：GitHub Pages，纯静态网站。所有数据由 GitHub Actions 定时抓取、计算，生成 JSON 后提交到仓库。**浏览器端不直接请求任何第三方 API**（既有 CORS 问题，也不稳定）。
2. **数据源**：只用免费、公开、尽量稳定的来源，**不使用 Alpha Vantage**。全站不需要任何密钥。AI 文本处理默认采用「手动模式」：在 Cursor 里用 Cursor 自带的 AI 额度完成（见第 7.5 节）。代码中保留 API 模式（DeepSeek）的接口，以后需要全自动时再启用；届时密钥放在 GitHub Secrets 的 `DEEPSEEK_API_KEY` 中，不能出现在前端和仓库里。
3. **范围**：只做美股，不做港股。
4. **时效**：财报发布后 1 天内完成更新即可。
5. **历史回填**：统一从「期末落在自然年 2021Q4 的财季」开始（MU 对应 FQ1-22）。
6. **数字诚实**：
   - 数字只能来自结构化来源或规则解析；
   - AI 只做文本理解（摘要、分类、翻译），产出必须附原句和出处；
   - 缺失就留空，或标「不可得 / 未披露」，**不编造、不插值，也不用其他来源默默补齐**。
7. **可扩展**：新增一只股票只需要三步：在 `config/watchlist.yaml` 加一行，新建 `config/companies/<T>.yaml`，跑一次回填。代码里不能写死 MU。

## 3. 技术栈与目录

- **前端**：Vite + TypeScript + 原生 DOM，不使用框架。图表用手写 SVG 或 div，以精确还原设计稿，不引入图表库。全文检索可以用 `minisearch`。
- **数据管道**：Python 3.11，依赖 `yfinance`、`requests`、`pandas`、`pyyaml`、`beautifulsoup4`、`pdfplumber`、`lxml`。
- **测试**：pytest 测口径计算，vitest 测格式化函数。

```
repo/
├─ config/
│  ├─ watchlist.yaml          # 股票池与分组
│  ├─ companies/<T>.yaml      # 每只股票：CIK、财季、发布时段、XBRL 映射、指标、指引、覆盖
│  ├─ sources.yaml            # 数据源清单（生成数据说明页）
│  ├─ red_rules.yaml          # 红色公告规则
│  ├─ analysts.yaml           # 分析师姓名与机构校正表
│  └─ notes/<T>.yaml          # 人工笔记：复盘笔记、本期关注的人工确认
├─ ai/                        # AI 任务区（见 01 第 7.5 节）
│  ├─ tasks/<T>/<FQ>/<task>.md      # 任务包：prompt + 输入原文 + 输出格式，由脚本生成
│  └─ outputs/<T>/<FQ>/<task>.json  # AI 输出，在 Cursor 中生成，经校验后提交
├─ data/                      # 只由脚本写入，提交进仓库
│  ├─ _status.json
│  ├─ raw/                    # 原始抓取结果（新闻稿 HTML、准备稿 PDF 文本、文字稿），用于审计和重新解析
│  ├─ prices/ financials/ releases/ calls/ snapshots/ events/ filings/ actuals/ history/
│  │                         # 各页面文件可以在此基础上补充子目录，需在页面文件中说明
│  └─ pages/                  # 前端直接消费的聚合 JSON（每页一个）
├─ scripts/
│  ├─ lib/ fiscal.py fmt.py io.py http.py edgar.py ai.py status.py
│  ├─ prompts/                # AI 的 prompt 模板，文件名带版本号，如 call_points_v3.md
│  ├─ ai_prepare.py           # 生成待处理的 AI 任务包
│  └─ ai_check.py             # 校验 AI 输出（结构、出处、数字反查）
│  ├─ fetch_*.py              # 抓取
│  └─ build_*.py              # 生成 pages/*.json
├─ web/ (index.html, vite.config.ts, src/...)
├─ tests/
└─ .github/workflows/ data.yml, earnings-night.yml, pages.yml
```

**前端**：
- 使用 hash 路由：`#/`（观察池）、`#/MU`（财报解读）、`#/MU/financials`、`#/MU/call`、`#/MU/call/FQ3-26`、`#/MU/consensus`、`#/MU/price`、`#/sources`。
- Vite 的 `base` 设为 `/<仓库名>/`；读取数据时用相对路径 `./data/pages/...`；构建时把 `data/pages` 复制到产物中。
- **前端不做口径计算**。所有同比、环比、超预期、n.m. 判断都在 Python 中完成，JSON 里直接给出显示字符串和颜色类别（`up` / `down` / `flat` / `na`）。前端只负责渲染和交互。唯一的例外是用户输入后需要即时计算的地方（例如 Forward PE 的股价输入框）。

## 4. 视觉规范

### 4.1 Design tokens（`web/src/styles/tokens.css`）

```css
:root{
  --bg:#F4F5F7; --card:#FFFFFF; --ink:#15181D; --ink-2:#3A414C;
  --muted:#5B6370; --faint:#8A93A0; --placeholder:#B0B6C0;
  --line:#E2E5EA; --line-2:#EEF0F3; --axis:#D5D9E0; --row-sub:#F9FAFB; --row-sec:#FBFBFC;
  --up:#1D4ED8; --up-dark:#1E3A8A; --up-mid:#3B6FE0; --up-light:#8DAAF0; --up-pale:#C9D6F7;
  --down:#C2410C; --warn:#9A6700; --alert:#B91C1C;
  --sel-bg:#EEF2FD; --sel-ring:#E8EEFC;
  --est-bg:#EEF3FD; --est-bar:#DCE5FB; --act-bar:#8A93A0; --hist-bar:#9DB5F2;
  --seg-bg:#E6E8EC; --banner-bg:#FDF6EC; --banner-ink:#7C3A0A;
  --header-bg:#15181D; --header-chip:#2A3039; --header-input:#262B33;
  --tag-new-bg:#E6F4EA; --tag-new-ink:#22543D;     /* 新增 */
  --tag-up-bg:#E8EEFC;  --tag-up-ink:#1E3A8A;      /* 强化 / 上调 */
  --tag-chg-bg:#FDF0E6; --tag-chg-ink:#9A3412;     /* 变化 / 转弱 */
  --ok-bg:#E6F4EA; --ok-ink:#22543D; --mid-bg:#FDF3E1; --mid-ink:#7B4A0E; --bad-bg:#FDE8E8; --bad-ink:#8A1C1C;
  --font-sans:'Noto Sans SC',system-ui,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,monospace;
}
```

### 4.2 排版与布局

- **字体**：通过 Google Fonts 加载 `Noto Sans SC`（400/500/700）和 `IBM Plex Mono`（400/500/600）。**所有数字都用等宽字体。**
- **字号**：
  - 正文 14px，行高 1.5；
  - H1 28px/700（股票代码）；
  - H2 22px/700，前面带区块序号，例如「1 回顾」；
  - 区块副标题 13px，颜色 `--muted`；
  - 表格 13px；表头 12px，颜色 `--muted`，字重 500；脚注 12px。
- **布局**：
  - 内容最大宽度 1360px，左右 padding 24px；
  - 区块之间 gap 40px，区块内部 gap 14px；
  - 卡片圆角 10px，1px `--line` 边框，内边距 14–20px。
- **禁止**：渐变、emoji 图标、红绿配色。图标一律用内联描边 SVG。

### 4.3 颜色语义（全站统一）

- 蓝色 `--up`：增加、好于预期、上调。
- 橙色 `--down`：减少、差于预期、下调。
- 灰色 `--faint`：无数据、n.m.、占位符。
- 琥珀色 `--warn`：两个来源的数据有分歧（⚠）。
- 红色 `--alert`：**只用于**观察池的「红色公告」徽标和色条。
- **共识 / 预估值**：表格中用 `--est-bg` 底色；柱状图中用 `--est-bar` 填充加 1.5px 虚线 `--up` 边框。

## 5. 公共组件

| 组件 | 规格 |
|---|---|
| `AppHeader` | 深色 `--header-bg`，高 56px。左侧：logo「财报台」、导航「观察池」「数据说明」（当前页高亮）。右侧：搜索框，占位文字「输入代码进入个股」，在 watchlist 中做前缀匹配，回车后跳转。 |
| `StockHeader` | 第 1 行：面包屑「观察池 / MU」。第 2 行：代码（H1）、英文名、中文名、标签「纳斯达克 · 存储」；右侧显示「最新财报 FQ4-26 · 2026-09-30 盘后发布」。第 3 行：指标条，包括股价、市值、EV、Forward PE、做空比例（标注日期）、下次财报，以及「更多指标 ▾」（展开后显示 52 周区间、股息 $0.15/季、Beta、隐含波动等）。 |
| `StockTabs` | 财报解读 / 财务报表 / 电话会 / 分析师预期 / 股价反应。选中项为 2px `--up` 下划线、`--ink` 颜色、字重 500。切换 tab 时保持当前股票。 |
| `Segmented` | 外层 `--seg-bg` 背景、圆角 8px、padding 3px。按钮高 32px、圆角 6px、padding 0 12–14px。选中项为白底、`--ink`、字重 500，阴影 `0 1px 2px rgba(0,0,0,.08)`。必须是真正的 `<button>`，并设置 `aria-pressed`，外层加 `role="group"` 和 `aria-label`。 |
| `ToggleChip` | 复选型开关（例如财务报表的「✓ 同比」）。选中时 `--sel-bg` 背景、1.5px `--up` 边框、`--up-dark` 文字；禁用时透明度 0.45。 |
| `KpiCard` | 结构：标签（12px muted）、主值（20–24px mono）、副行（12px）。 |
| `DataTable` | 支持排序表头、外层 `overflow-x:auto`、行类型样式、子行（↳ 同比 / 环比）、占位符置灰、`title` 悬停说明。 |
| `Placeholder` | 统一渲染 `[ ]`、`不可得`、`未披露`、`n.m.`、`—`，颜色 `--faint`，`title` 中写明原因。 |
| `Tag` | 圆角胶囊，11px，字重 500。语义色见 tokens（新增 / 强化 / 转弱 / 变化 / 上调）。 |
| `FooterNote` | 页尾 12px 说明，写明数据来源和颜色约定。 |
| `Banner` | 米黄底的提示条（`--banner-bg` / `--banner-ink`），用于快照时间、待回填等说明。 |

**响应式**：宽度 < 900px 时，多列网格变为单列，表格在卡片内部横向滚动，`body` 不能出现横向滚动。宽度 ≥ 1440px 时，内容居中。

## 6. 全站口径

| 项 | 规则 |
|---|---|
| 财期命名 | `FQn-YY`，按公司财年。例如 MU 的 FQ4-26 截至 2026-09-03。年度写作 `FY26`；财务报表页的年度列写作 `FY2026`。 |
| 同比 | 与去年同期比较。 |
| 环比 | 与上一期比较。资产负债表科目比较的是上季末。年度视图没有环比。 |
| 金额 vs 比率 | 金额类的变化用 `%`；比率类（毛利率、利润率、FCF 率等）的变化用 `pp`；天数类用「天」。 |
| n.m. | 基数 ≤ 0，或当期 < 0 且基数 > 0（符号翻转）时显示 `n.m.`。 |
| 缺失 | 缺少基数显示 `—`，缺少数值显示 `[ ]`。 |
| 百分比精度 | 绝对值 ≥ 1000% 时取整（`+1003%`）；否则保留 1 位小数（`+30.8%`）。分析师预期页的四宫格例外，统一取整，以对齐 Bloomberg 的风格。 |
| 负号 | 一律使用 `−`（U+2212），不用连字符。 |
| 金额单位 | 表格内由单位切换控制（$M / $B）；卡片里写成 `$54.23B`。 |
| GAAP / Non-GAAP | 每个指标都必须标注口径。EPS 默认用 Non-GAAP（与市场共识口径一致）；利润表科目默认用 GAAP。 |
| 发布前共识 | 发布时间点之前最后一份共识快照，详见 `06_consensus.md`。 |
| 时间 | 存储时一律用 UTC。页面展示用北京时间，标注「北京」；财报发布时段（盘前 / 盘后）按美东时间判断。 |

## 7. 数据管道基础设施

### 7.1 `config/companies/<T>.yaml` 骨架

```yaml
ticker: MU
cik: 723125
name_en: Micron Technology
name_zh: 美光科技
exchange: 纳斯达克
sector: 存储
fiscal:
  quarter_end_months: [11, 2, 5, 8]     # Q1..Q4 大致的结束月份
  fy_label: end_year                     # FY26 = 截至 2026 年的财年
release_timing: after_close              # after_close / before_open
backfill_from: FQ1-22
ir:
  prepared_remarks_url_pattern: null     # 准备稿 PDF 页面（各期不同，可以手工填）
xbrl_map: {}                              # 见 04_financials.md
metrics: {}                               # 见 03_review.md
guidance: {}                              # 见 03_review.md / 06_consensus.md
overrides: {}                             # 手工覆盖自动数据，必须写明来源和理由
```

### 7.2 `scripts/lib/fiscal.py`（核心，必须有测试）

- 输入期末日期 → 输出财期名。**以 10-Q / 10-K 中的 `fp`、`fy`、期末日期为准**，不要只靠月份推算，因为 MU 的财年在 8 月底到 9 月初之间浮动。
- 提供相对标签到绝对财期的换算（例如 Yahoo 的 `0q`、`+1q`）。
- 提供「上一期」「去年同期」的查找函数。

### 7.3 运行状态 `data/_status.json`

```json
{ "sources": { "yahoo_consensus": {"last_ok": "2026-10-01T22:41Z", "last_err": null, "err_msg": null}, "...": {} } }
```

- 每个 fetch 脚本单独用 try/except 包住，**失败时保留旧数据，绝不用空数据覆盖**。
- 失败信息写进 `_status.json`，由数据说明页展示。

### 7.4 HTTP 规范（`lib/http.py`）

- 统一重试：3 次，指数退避。
- 访问 SEC 时带 `User-Agent: "<项目名> <你的邮箱>"`，每秒不超过 10 次请求。
- 访问非官方页面（MarketBeat、Nasdaq、第三方文字稿）时带浏览器 UA，失败就跳过并记录，**不能让整个任务失败**。
- 原始响应保存到 `data/raw/`，便于审计和重新解析。

### 7.5 AI 处理：手动模式（默认）与 API 模式（预留）

**为什么不能在 GitHub Actions 里直接用 Cursor 的额度**：Cursor 的 AI 额度只能在 Cursor 编辑器里由人发起使用，不提供给服务器或脚本调用的 API。而 Actions 是在 GitHub 的服务器上自动运行的，所以自动化流程无法调用 Cursor。

**因此 AI 步骤和其他数据管道分开**：

- 抓取和计算全部在 Actions 中自动完成。
- 需要 AI 的地方，由脚本生成「任务包」，然后**由你在 Cursor 中用一句话触发处理**。
- 处理结果经脚本校验后提交。

`config/ai.yaml`：

```yaml
provider: manual          # manual（默认，用 Cursor）| deepseek（预留）
deepseek:
  model: deepseek-chat
  base_url: https://api.deepseek.com
  api_key_env: DEEPSEEK_API_KEY
```

#### 手动模式流程

1. **生成任务包**（自动）：`scripts/ai_prepare.py` 在 `data.yml` 中运行。它发现「有了新原文但还没有 AI 输出」的财报，就生成 `ai/tasks/<T>/<FQ>/<task>.md`。每个任务包都是自包含的，包括：
   - 任务说明：引用 `scripts/prompts/` 中带版本号的模板；
   - 输入：原文段落（带段落 id）、已算好的数字；
   - 输出的 JSON schema；
   - 输出路径。
2. **提醒**（自动）：有新任务时，`data.yml` 自动开一个 GitHub Issue，标题例如「MU FQ1-27 有 6 个 AI 任务待处理」，你会收到邮件。页面上对应位置显示「AI 解读待生成」（灰色）。
3. **在 Cursor 中处理**（手动，每次财报约 5–15 分钟）：`git pull` 后，在 Cursor 里说：
   > 处理 ai/tasks/ 下所有还没有对应输出的任务：逐个读取任务包，严格按其中的 prompt 和 schema 生成 JSON，写到指定的输出路径。完成后运行 `python scripts/ai_check.py`，修正所有报错，直到全部通过。
4. **校验**（自动 + 手动）：`scripts/ai_check.py` 检查四项：
   - JSON 结构；
   - 每条都有 `source_ref` 且所指段落存在；
   - 输出中出现的每个数字都能在所引段落或输入数据中找到；
   - 不包含评价词表中的词。

   不合格的条目会被列出，交给 Cursor 修正。
5. **提交**：commit 并 push 后，`data.yml` 的 build 步骤读取 `ai/outputs/`，合并进页面 JSON，并关闭对应的 Issue。

#### 两种模式共用的规则

- `scripts/lib/ai.py` 定义统一接口 `run_task(task_path) -> output_path`：
  - `manual` 模式下只检查输出是否已经存在；
  - `deepseek` 模式下读取任务包，调用 API，写出结果。
  - **任务包和输出的格式在两种模式下完全相同**，以后切换到 API 模式不需要改其他代码。
- 每条输出记录都要包含：`source_ref`（原文段落 id 或时间戳）、`quote`（原句）、`prompt_version`、`model`。手动模式下 `model` 填 `"cursor-manual"`。
- **AI 不产生数字**：输出中出现的每个数字都必须能在输入里找到，找不到就丢弃这一条（由 `ai_check.py` 执行）。
- 输出以输入内容的哈希值命名或记录哈希。输入没有变化时不重新生成；prompt 版本升级后，旧输出保留，直到重新生成。
- **历史回填**（例如 MU 的 20 场电话会）一次性工作量较大，可以分批在 Cursor 中处理，每次处理一个季度。

#### 哪些地方用到 AI

| 页面 | AI 任务 | 不处理时的显示 |
|---|---|---|
| 03 财报解读 | 总结段落、「为什么」、子面板解读、指引原因、本期关注草稿 | 「AI 解读待生成」，数字部分照常显示 |
| 05 电话会 | 要点、新增 / 变化标签、讲话人总结、问答摘要与主题、中文翻译 | 要点与问答区显示「待生成」；原文 tab 照常显示英文 |
| 07 股价反应 | 复盘笔记草稿 | 显示「[一句话：市场在交易什么]」占位 |

页面上的所有数字都不依赖 AI，所以 AI 部分没有处理时，网站其他部分照常更新。

### 7.6 GitHub Actions

| Workflow | 触发 | 内容 |
|---|---|---|
| `data.yml` | `30 22 * * 1-5`（UTC，美东收盘后）加手动触发 | 跑所有 fetch 和 build；只在数据有变化时 commit，提交人为 `github-actions[bot]` |
| `earnings-night.yml` | 每 30 分钟检查一次「今天是否有观察池内股票发财报」 | 财报日：盘后价快照、抓取新闻稿和准备稿；财报前一日：快照期权隐含波动 |
| `pages.yml` | push 到 main 时 | 构建前端并通过 `actions/deploy-pages` 部署 |

注意：
- GitHub 的 cron 可能延迟 10–30 分钟。
- 仓库 60 天没有活动，定时任务会被暂停；每日 commit 可以避免这个问题。

## 8. 样例数据规则（P0 阶段）

- 从各页设计稿 `class Component ... renderVals()` 中提取样例数据，放到 `web/public/sample/<page>.json`，**结构必须和正式的 `data/pages/...json` 完全一致**。这样以后切换到真实数据时，前端不用改。
- 设计稿里的 `[ ]`、`[x.x]`、`[±x%]`、`[日期]` 在样例中写成 `null`，由前端统一渲染成占位符。

## 9. 分阶段计划与总验收

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | 外壳、公共组件、tokens、路由；7 页用样例数据完成静态还原 | 与设计稿逐页对照，列出差异；390px 宽度下无横向溢出 |
| P1 | `fiscal.py`、价格、XBRL → 财务报表页；StockHeader 接入真实数据 | 见 `04` 的验收清单 |
| P2 | 共识快照 → 分析师预期页；观察池的 NTM、修正、Forward PE 列 | 见 `06` |
| P3 | 新闻稿解析、事件快照 → 股价反应页、财报解读的数字部分 | 见 `07`、`03` |
| P4 | 准备稿、文字稿、AI 任务包与校验（手动模式）→ 电话会页、财报解读的 AI 部分 | 见 `05`、`03`；完整跑通一次「生成任务包 → Cursor 处理 → 校验 → 页面显示」 |
| P5 | 8-K、Form 4、红色规则、ics → 观察池完整功能 | 见 `02` |
| P6 | 数据说明页、`_status` 展示、失败告警（可选：自动开 GitHub Issue） | 见 `08` |

**总验收**：
- [ ] 任意一个数字都能追溯到 `data/` 中的文件，以及 `sources.yaml` 中的来源
- [ ] 所有 AI 内容都能点回原文，并且带 prompt 版本
- [ ] 颜色、n.m.、pp / %、负号、单位在全站保持一致
- [ ] 断开任一来源后，旧数据保留，数据说明页显示失败状态
- [ ] 新增一只股票不需要改代码
