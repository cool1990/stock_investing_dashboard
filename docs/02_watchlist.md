# 02 观察池（首页）

- 路由：`#/`
- 设计稿：`docs/design/watchlist-mockup.dc.html`
- 通用约定：`01_common.md`

## 1. 目的

用一屏回答四个问题：
1. 关注的股票里，谁的盈利预期在被上调或下调？
2. 谁出了重大公告？
3. 谁快要发财报？
4. 最近发布财报的公司，结果是超预期还是不及预期？

## 2. 页面结构

```
AppHeader（「观察池」高亮）
──────────────────────────────────────────────────────────────────────
观察池                                [全部|AI 硬件|软件|平台]  [+ 添加股票]
8 只股票 · 数据截至 [2026-10-01 07:00 北京]（美股前一交易日收盘）

┌红色公告（近 7 天）┐┌未来 30 天财报─┐┌EPS 预期上调/下调（30 天）┐┌待验证跟踪项┐
│ 3   涉及 2 只股票  ││ 5  最近 CDNS·10-xx││ 4 / 1   按 NTM 共识变化计 ││ 6  来自各股…│
└──────────────────┘└───────────────┘└──────────────────────────┘└────────────┘

指标对比                                   点击表头排序 · 点击代码进入个股  [选择列 ▾]
┌──────────────────────────────────────────────────────────────────────────────┐
│代码/名称 分组 股价 1D YTD 市值 NTM EPS 共识 EPS修正30D ForwardPE▼ 做空比例 最近财报 财报次日 下次财报 红色公告│
│MU Micron 存储 …                                     +5.4%  …   [2026-12]   (2)          │
└──────────────────────────────────────────────────────────────────────────────┘
脚注：Forward PE = 股价 ÷ NTM 共识 EPS（自己的每日快照）；最近财报 = EPS 超预期幅度

┌公告与新闻 ─── [只看红色|全部] ───────────┐ ┌财报日历 ─── 导出到日历（.ics）┐
│▌09-30 MU 8-K · 2.02 业绩                 │ │ 观察池内未来 60 天 · 北京时间  │
│  FQ4-26 收入 $54.2B，超共识 5.6%…        │ │ 10-xx 周x 盘后 CDNS FQ3 · 共识…│
│  触发：业绩发布 + 指引上调               │ │ …                              │
│▌…                                        │ ├最近发布 ────────────────────────┤
│红色规则说明（小字）                      │ │ 09-30 MU FQ4-26 · EPS/收入 +5.4% +5.6% →│
└──────────────────────────────────────────┘ └────────────────────────────────┘
```

右侧栏上下排列两张卡：「财报日历」和「最近发布」。

### 2.1 标题行

- **分组切换**：`Segmented` 组件，选项为全部 / AI 硬件 / 软件 / 平台，分组来自 `watchlist.yaml`。切换分组时，KPI、表格、公告、日历**全部按分组过滤**。
- **「+ 添加股票」**：链接到 GitHub 上 `config/watchlist.yaml` 的编辑页（`https://github.com/<owner>/<repo>/edit/main/config/watchlist.yaml`），新标签页打开。

### 2.2 四个 KPI 卡

| 卡 | 主值 | 副行 | 计算 |
|---|---|---|---|
| 红色公告（近 7 天） | 条数 | 涉及 N 只股票 | `filings` 中 `red=true` 且日期在 7 天内的条目 |
| 未来 30 天财报 | 数量 | 最近一只：代码 · 日期 | 财报日历中未来 30 天的条目 |
| EPS 预期上调 / 下调（30 天） | 上调股票数 / 下调股票数 | 按 NTM 共识变化计 | 每只股票当前 NTM EPS 与 30 天前快照对比，> +1% 计为上调，< −1% 计为下调，阈值写在配置里 |
| 待验证跟踪项 | 条数 | 来自各股「财报解读 · 本期关注」 | 汇总各股 `review.json` 中的关注项，`notes/<T>.yaml` 中标记为已解决的不计入 |

### 2.3 指标对比表

| 列 | 内容 / 格式 | 来源 |
|---|---|---|
| 代码 / 名称 | 代码加粗；名称小字。点击进入 `#/<T>`；**还没有接入个股页的股票不可点击**，显示为灰色 | watchlist |
| 分组 | 细分标签 | watchlist |
| 股价 | `$xxx.xx` | prices |
| 1D、YTD | 涨跌幅，蓝 / 橙 | prices |
| 市值 | `$xxxB` 或 `$x.xxT` | 股价 × 最新股本（XBRL 的 dei:EntityCommonStockSharesOutstanding；缺失时用 yfinance） |
| NTM EPS 共识 | `$x.xx` | consensus（NTM 算法见 06） |
| EPS 修正 30D | 当前 NTM ÷ 30 天前 NTM − 1 | snapshots |
| Forward PE | 股价 ÷ NTM EPS，保留 1 位；EPS ≤ 0 时显示 n.m.。**默认按此列升序** | 计算 |
| 做空比例 | `x.x%`，`title` 中显示披露日期 | yfinance（FINRA 半月披露） |
| 最近财报 | 第一行是日期，第二行是 EPS 超预期幅度（蓝 / 橙） | history |
| 财报次日 | 次日涨跌 | price 页同源 |
| 下次财报 | `YYYY-MM-DD`；日期未确认时写成 `[YYYY-MM]` 并显示灰色 | calendar |
| 红色公告 | 近 7 天的红色公告条数。> 0 时用红色圆形徽标（`--alert` 底、白字）；为 0 时显示灰色 `0` | filings |

交互：
- 表头可点击排序，再点一次切换升序 / 降序，`null` 值永远排在最后。
- 「选择列」是下拉复选框，用户的选择存到 localStorage 的 `watchlist.cols` 中。

### 2.4 公告与新闻

- 支持「只看红色」和「全部」两种模式，默认只看红色。
- 每条的结构：左侧 4px 色条（红色 `--alert`，或灰色 `--axis`）、日期、代码、类型标签（如 `8-K · 2.02 业绩`、`电话会`、`新闻稿`、`Form 4`、`评级`）、标题（一行）、触发原因（小字，例如「业绩发布 + 指引上调」）。
- 默认显示最近 30 天，最多 30 条，底部有「加载更多」。
- 卡片底部附上红色规则说明。规则内容由 `red_rules.yaml` 生成，不要写死在页面里。

### 2.5 财报日历

- 显示观察池内未来 60 天的财报。每条包含：北京日期 + 星期、盘前 / 盘后、代码、财期 · 共识 EPS · 隐含波动（如果有）。
- 「导出到日历（.ics）」链接到 `data/pages/calendar.ics`，由管道生成。每个事件包含：标题「MU FQ1-27 财报（盘后）」；开始时间为美东 16:05（盘后）或 08:00（盘前），转换成 UTC；描述里写共识 EPS。

### 2.6 最近发布

- 列出最近 6 次财报发布（覆盖观察池所有股票）。每条包含：日期、代码、财期 · EPS / 收入、EPS 超预期幅度、收入超预期幅度、跳转箭头。点击后进入该股票该期的财报解读。

## 3. 数据来源

| 数据 | 来源 | 说明 |
|---|---|---|
| 股票池、分组 | `config/watchlist.yaml` | 手工维护 |
| 股价、1D、YTD | yfinance 日线（Stooq 作备份） | 每日 |
| 股本 / 市值 | EDGAR `dei:EntityCommonStockSharesOutstanding`，缺失时用 yfinance `sharesOutstanding` | 季度 |
| NTM EPS、30 天修正 | 每日共识快照（见 06） | 每日 |
| 做空比例 | yfinance `info['shortPercentOfFloat']` 及其日期字段 | 半月 |
| 下次财报日 | yfinance `get_earnings_dates`；公司 IR 公告可以在 `companies/<T>.yaml` 的 `next_earnings` 里手工覆盖 | 每日 |
| 公告 | EDGAR submissions API：`https://data.sec.gov/submissions/CIK##########.json`（8-K 附 item 编号、Form 4）。**在本仓库内新建 EDGAR 抓取**（P5），股票池以 `config/watchlist.yaml` 为准；新闻稿标题取 EX-99.1 的首段 | 每日 |
| Form 4 公开市场买入 | 解析 Form 4 XML：`transactionCode == "P"` 表示公开市场买入 | 每日 |
| 评级 / 目标价变化 | yfinance `upgrades_downgrades` | 每日，非稳定来源 |
| 电话会要点类公告 | 来自 05 的电话会解析结果（例如「资本回报政策变化」） | 财报日 |

## 4. 红色规则（`config/red_rules.yaml`）

```yaml
rules:
  - id: 8k_202
    label: 业绩发布
    match: { form: 8-K, items: ["2.02"] }
  - id: 8k_101
    label: 重大协议
    match: { form: 8-K, items: ["1.01"] }
  - id: 8k_502
    label: 高管变动
    match: { form: 8-K, items: ["5.02"] }
  - id: guide_vs_cons
    label: 指引显著偏离共识
    match: { source: release, guidance_vs_consensus_abs_gt: 0.05 }
  - id: insider_buy
    label: 内部人公开市场买入
    match: { form: "4", transaction_code: P, value_usd_gt: 100000 }
  - id: rating_change
    label: 评级变化
    match: { source: rating, action: [up, down] }
  - id: legal
    label: 监管 / 诉讼
    match: { form: 8-K, items: ["8.01"], keywords_any: [SEC, subpoena, lawsuit, investigation] }
```

每条公告的 `why` 字段由命中的规则 label 拼接而成。

## 5. 数据模型 `data/pages/watchlist.json`

```json
{
  "as_of_bj": "2026-10-01 07:00",
  "groups": [{"id":"all","label":"全部"},{"id":"hw","label":"AI 硬件"},{"id":"sw","label":"软件"},{"id":"pf","label":"平台"}],
  "kpi": { "red7d": {"n": 3, "tickers": 2}, "earn30d": {"n": 5, "next": {"t":"CDNS","d":"2026-10-xx"}},
           "rev30d": {"up": 4, "down": 1}, "todo": 6 },
  "stocks": [ { "t":"MU","name":"Micron","group":"hw","sub":"存储","has_page":true,
                "price":null,"d1":null,"ytd":null,"mcap":null,"ntm_eps":null,"rev30":null,"fpe":null,
                "short":null,"short_date":null,"last":{"d":"2026-09-30","q":"FQ4-26","eps_surp":0.054},
                "react":null,"next":{"d":null,"approx":"2026-12"},"red7d":2 } ],
  "news": [ {"d":"2026-09-30","t":"MU","type":"8-K · 2.02 业绩","title":"…","why":"业绩发布 + 指引上调","red":true,"url":"https://www.sec.gov/…"} ],
  "calendar": [ {"d":"2026-10-xx","t":"CDNS","timing":"after_close","q":"FQ3","cons_eps":null,"iv":null} ],
  "recent": [ {"d":"2026-09-30","t":"MU","q":"FQ4-26","eps_surp":0.054,"rev_surp":0.056} ]
}
```

数值字段一律存原始数值；**颜色类别由后端（Python）统一给出**（`up` / `down` / `flat` / `na`），前端只按色类渲染。全站统一，不在前端自行根据符号判断（唯一例外见 `01_common.md`：Forward PE 股价输入框）。

## 6. 注意事项

1. 每家公司的财年不同。「最近财报」列显示的是各自最近一期，不要按日历季度对齐。
2. 观察池中个股页未上线的股票（`has_page: false`），仍然要显示行情、共识和公告，只是代码不可点击。
3. 做空比例每半月更新一次，必须显示披露日期，避免被误认为是实时数据。
4. 公告标题过长时截断为一行，`title` 中显示全文。点击打开 SEC 原文链接。
5. 「待验证跟踪项」依赖 `03` 的「本期关注」功能。该功能没有完成之前显示 `[ ]`。

## 7. 验收清单

- [ ] 切换分组时，KPI、表格、公告、日历同步过滤
- [ ] 表格默认按 Forward PE 升序；`null` 值永远排在最后；列选择在刷新后仍然保留
- [ ] 红色公告的条数与 `filings` 中近 7 天红色条目一致
- [ ] `calendar.ics` 可以导入 Google 日历和 Apple 日历，时间正确
- [ ] MU 一行的「最近财报 +5.4%」与 06 历史区块的数据一致
