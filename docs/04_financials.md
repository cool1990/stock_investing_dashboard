# 04 财务报表

- 路由：`#/MU/financials`
- 设计稿：`docs/design/results-mockup.dc.html`
- 通用约定：`01_common.md`

## 1. 目的

提供完整、可导出、口径清楚的四张表：利润表、资产负债表、现金流量表、股东权益变动表，外加 Non-GAAP 与关键衍生指标。用户可以：
- 自己核对财报解读页的每一个数；
- 看长期趋势（从 FQ1-22 起）；
- 导出 CSV 自己做分析。

## 2. 页面结构

```
AppHeader / StockHeader / StockTabs（财务报表）

[利润表|资产负债表|现金流量表|股东权益表]   [单季|累计|年度]   [$M|$B]
显示 [✓同比] [✓环比]   范围 [最近 5 期 ▾]   [✓隐藏全空行]   [导出 CSV]
提示：单季：流量科目由 10-Q 累计数相减得到；资产负债表取季末余额，环比为较上季末。

┌利润表（季度）───────────────────── ■增加 ■减少 ─── 单位：$ 百万，EPS 为 $ ┐
│ 项目            FQ4-25    FQ1-26    FQ2-26    FQ3-26    FQ4-26             │
│ 营业收入        11,315    13,643    23,860    41,456    54,229   （合计行加粗）│
│  ↳ 同比         +46.0%    +56.6%   +196.3%   +345.7%   +379.3%  （子行，小字）│
│  ↳ 环比         …                                                          │
│ 销售成本         6,261      [ ]       [ ]      6,400     7,182             │
│ 毛利             …                                                          │
│   毛利率        44.7%     56.0%  …          （推算项：斜体灰字）            │
│ …                                                                          │
│ NON-GAAP（分组标题，12px 深蓝粗体，浅灰底）                                 │
│   营业利润 / 净利润 / 摊薄 EPS（缩进行）                                    │
│ 注释：同比基数取自…                                                        │
└────────────────────────────────────────────────────────────────────────────┘
规则说明（页脚）
```

### 2.1 控件

| 控件 | 选项 | 行为 |
|---|---|---|
| 报表 | 利润表 / 资产负债表 / 现金流量表 / 股东权益表 | `Segmented` |
| 期间 | 单季 / 累计 / 年度 | 累计 = 财年初至该季末（3M / 6M / 9M / 12M）。资产负债表和权益表是时点数，「累计」视图与单季相同，并在提示行说明 |
| 单位 | $M / $B | $M 取整并加千分位；$B 保留 2 位。EPS 始终显示 $，保留 2 位；天数是整数 |
| 显示 | ✓ 同比、✓ 环比 | `ToggleChip`。**环比只在单季视图下可用**，其他视图下禁用（透明度 0.45，`aria-disabled`） |
| 范围 | 最近 5 期 / 最近 12 期 / 全部（FQ1-22 起） | 列数超过可视宽度时，表格在卡片内部横向滚动，第一列（项目）固定 |
| 隐藏全空行 | 开关，默认开启 | 所有列都为 `null` 的行隐藏，分组标题行保留 |
| 导出 CSV | — | 在前端按**当前视图**生成，包括所选报表、期间、单位、范围以及是否含同比 / 环比。文件名为 `MU_利润表_单季_2026-10-01.csv`，使用 UTF-8 BOM，确保 Excel 打开中文不乱码 |

提示行（`modeNote`）根据视图显示不同说明：
- 单季：「单季：流量科目由 10-Q 累计数相减得到；资产负债表取季末余额，环比为较上季末。」
- 累计：「累计 = 财年初至该季末。同比与上年同期累计相比。」（资产负债表和权益表：「资产负债表、权益表是时点数，累计视图与单季相同。」）
- 年度：「年度：财年（截至 8 月底 / 9 月初）。」

### 2.2 表格

- **表头**：期间名。资产负债表的表头加期末日期，例如「FQ4-25 · 08-28」；累计视图写作「FQ1-26 · 3M」。
- **行类型**：

| 类型 | 用途 | 样式 |
|---|---|---|
| `b` | 合计行（营业收入、毛利、营业利润、净利润、EPS、总资产等） | 加粗 |
| `''` | 普通科目 | 常规 |
| `d` | 推算或衍生项（毛利率、FCF 率、净现金、DIO、其他营业费用（推算）） | 斜体，`--muted`，缩进 18px，`title` 中显示公式 |
| `s` | 分组标题（资产 / 负债与权益 / 经营活动 / 投资活动 / 筹资活动 / 自由现金流 / Non-GAAP / 关键衍生指标） | `--row-sec` 底色、12px、字重 700、`--up-dark` |
| `i` | 缩进项（Non-GAAP 下的科目） | 缩进 18px |

- **同比 / 环比子行**：显示在每个科目下面，名称写作「↳ 同比」「↳ 环比」，`--row-sub` 底色、12px。增加用蓝色，减少用橙色，`—` 和 n.m. 用灰色。比率类用 pp，天数类用「+9 天」。
- `null` 值显示 `[ ]`，颜色 `--placeholder`。
- 每张表底部有一条注释，说明回填状态和特殊口径。

### 2.3 各表的行（MU，来自设计稿；正式版由 `xbrl_map` 驱动）

**利润表**：
- 营业收入（b）、销售成本、毛利（b）、毛利率（d）、研发费用、销售及管理费用、其他营业费用（推算）（d）、营业利润（b）、营业利润率（d）、利息及其他收支、所得税、净利润（b）、净利润率（d）、摊薄 EPS（b）；
- 「Non-GAAP」分组：营业利润（i）、净利润（i）、摊薄 EPS（i）。

**资产负债表**：
- 「资产」分组：现金及现金等价物、短期投资、应收账款、存货、长期有价证券、固定资产净值、总资产（b）；
- 「负债与权益」分组：短期债务、长期债务、客户合同负债（非流动）、总负债（b）、股东权益（b）；
- 「关键衍生指标」分组：现金及投资合计（d）、有息债务合计（d）、净现金（d）、存货天数 DIO（d，天）。

**现金流量表**：
- 「经营活动」分组：净利润、折旧及摊销、股权激励、营运资本变动、经营活动现金流（b）；
- 「投资活动」分组：购建固定资产、政府补贴与合作方出资、净 Capex（支出，公司口径）（d）；
- 「筹资活动」分组：偿还债务、回购、股息；
- 「自由现金流」分组：调整后 FCF（公司口径）（b）、FCF 率（d）。

**股东权益变动表**：期初股东权益（b）、净利润、股权激励、回购、股息、其他综合收益、其他合计（推算）（d）、期末股东权益（b）、年化 ROE（d）。

## 3. 数据来源

| 数据 | 来源 | 方法 |
|---|---|---|
| GAAP 三大表 | `https://data.sec.gov/api/xbrl/companyfacts/CIK0000723125.json` | 按 `xbrl_map` 取 tag；10-Q 用 `fp=Q1/Q2/Q3`，10-K 用 `fp=FY` |
| 单季流量科目 | 同上 | 10-Q 中现金流量表**只有年初至今累计数**，利润表通常同时有单季和累计数。单季 = 本期累计 − 上期累计；Q4 = 10-K 全年 − Q3 累计 |
| Non-GAAP 行 | 新闻稿调节表（见 03） | 解析加反查 |
| 净 Capex、调整后 FCF（公司口径） | 新闻稿（公司自定义口径） | 解析 |
| 期末日期、财期 | XBRL 中的 `end`、`fp`、`fy`、`form` | — |

**`xbrl_map` 示例**（每个字段允许多个候选 tag，按顺序回退）：

```yaml
xbrl_map:
  revenue: [Revenues, RevenueFromContractWithCustomerExcludingAssessedTax]
  cogs: [CostOfGoodsAndServicesSold, CostOfRevenue]
  gross_profit: [GrossProfit]
  rnd: [ResearchAndDevelopmentExpense]
  sga: [SellingGeneralAndAdministrativeExpense]
  op_income: [OperatingIncomeLoss]
  net_income: [NetIncomeLoss]
  eps_diluted: [EarningsPerShareDiluted]
  shares_diluted: [WeightedAverageNumberOfDilutedSharesOutstanding]
  cash: [CashAndCashEquivalentsAtCarryingValue]
  st_investments: [ShortTermInvestments, AvailableForSaleSecuritiesDebtSecuritiesCurrent]
  receivables: [AccountsReceivableNetCurrent]
  inventory: [InventoryNet]
  lt_securities: [LongTermInvestments, AvailableForSaleSecuritiesDebtSecuritiesNoncurrent]
  ppe_net: [PropertyPlantAndEquipmentNet]
  total_assets: [Assets]
  st_debt: [LongTermDebtCurrent, DebtCurrent]
  lt_debt: [LongTermDebtNoncurrent]
  contract_liab_noncurrent: [ContractWithCustomerLiabilityNoncurrent]
  total_liabilities: [Liabilities]
  equity: [StockholdersEquity]
  cfo: [NetCashProvidedByUsedInOperatingActivities]
  capex_gross: [PaymentsToAcquirePropertyPlantAndEquipment]
  da: [DepreciationDepletionAndAmortization, DepreciationAndAmortization]
  sbc: [ShareBasedCompensation]
  buyback: [PaymentsForRepurchaseOfCommonStock]
  dividends: [PaymentsOfDividends, PaymentsOfDividendsCommonStock]
  debt_repay: [RepaymentsOfLongTermDebt, RepaymentsOfDebt]
```

**Cursor 首次实现时，先写一个诊断脚本**：列出 MU 在 companyfacts 中实际出现的全部 tag 及其覆盖期数，然后据此修正映射，最后把映射写进 `MU.yaml`。

## 4. 数据模型

### 4.1 `data/financials/<T>.json`（原始结构化数据）

```json
{ "periods": { "FQ4-26": { "end": "2026-09-03", "fy": 2026, "fp": "FY", "form": "10-K", "filed": "2026-10-xx",
                           "q":   { "revenue": 54229, "cfo": 43973, "...": 0 },
                           "ytd": { "revenue": 133188, "cfo": 89675 },
                           "bs":  { "cash": 38364 },
                           "derived": { "cfo": "fy_minus_9m" } } },
  "units": "USD millions" }
```

`derived` 字段记录每个单季值是怎么得到的：`reported`（直接披露）、`ytd_diff`（累计相减）、`fy_minus_9m`（全年减 9 个月），用于审计和悬停说明。

### 4.2 `data/pages/<T>/financials.json`

推荐**直接输出四张表、三种期间的「行定义 + 数值数组 + 同比 / 环比数组」**。前端只做单位换算、范围截取、隐藏空行和导出，这些都是纯展示行为。

```json
{ "tables": { "is": { "q": { "title":"利润表（季度）","cols":["FQ1-22","…","FQ4-26"],"col_end":["2021-12-02","…"],
                             "rows":[{"kind":"b","name":"营业收入","fmt":"amt","v":[…],"yoy":[…],"qoq":[…],"formula":null}],
                             "note":"…" },
                      "ytd": {}, "y": {} },
              "bs": {}, "cf": {}, "eq": {} },
  "mode_notes": { "q": "…", "ytd": "…", "y": "…", "bs_ytd": "…" } }
```

数值统一存百万美元；比率存百分数（例如 44.7）；EPS 存美元；天数存整数。

## 5. 计算口径

| 项 | 公式 |
|---|---|
| 毛利率 / 营业利润率 / 净利润率 | 科目 ÷ 营业收入 |
| 其他营业费用（推算） | 毛利 − 研发 − SG&A − 营业利润 |
| 现金及投资合计 | 现金 + 短期投资 + 长期有价证券 |
| 有息债务合计 | 短期债务 + 长期债务 |
| 净现金 | 现金及投资合计 − 有息债务合计 |
| DIO | 存货 ÷ 本季销售成本 × 本季天数（期末日期差） |
| 净 Capex（公司口径） | 购建 PP&E − 政府补贴与合作方出资（以新闻稿为准） |
| 调整后 FCF | 经营现金流 − 净 Capex |
| FCF 率 | 调整后 FCF ÷ 营业收入 |
| 其他合计（权益表） | 期末 − 期初 − 净利润（接入完整科目后改为逐项列示） |
| 年化 ROE | 单季净利润 × 4 ÷ 平均股东权益 |
| 同比（累计视图） | 与上年同期累计比较 |
| 环比（资产负债表） | 与上季末比较 |

## 6. 注意事项

1. **重述**：同一期间可能出现在多份文件中（后续的 10-Q 会重述以前年度）。默认取 `filed` 最新的值，同时在 `title` 中显示「原报 x，重述为 y」。
2. **累计相减失败**：只要任何一侧缺失，单季值就留空 `[ ]`，**不能用其他来源填补**。
3. **EPS 不可相加**：累计和年度 EPS 都取报表原值；单季 EPS 取 10-Q 中直接披露的单季数。
4. **财年长度**：MU 部分财年有 53 周，DIO 的天数用实际期末日期差，不能固定写 91 天。
5. **符号**：XBRL 中的支出类 tag 是正数（例如 `PaymentsToAcquirePropertyPlantAndEquipment`），在现金流量表中按「流出为负」显示，并在注释中说明。
6. **Non-GAAP 行不能用 XBRL 补**，只能来自新闻稿。
7. **导出的 CSV** 必须与当前显示完全一致，包括单位，并在第一行写明单位和口径。

## 7. 验收清单

- [ ] FQ4-26 利润表：营收 54,229、净利润 37,701、摊薄 EPS 32.87，与 10-K 一致；Non-GAAP EPS 为 33.42
- [ ] FQ4-26 单季经营现金流 43,973 = FY26 的 89,675 − 9 个月累计 45,702
- [ ] 以 FY2023 为基数的同比显示 n.m.（因为 FY23 亏损）
- [ ] 环比在累计和年度视图下禁用
- [ ] 从 FQ1-22 起的「全部」范围可以横向滚动，第一列固定
- [ ] 导出的 CSV 用 Excel 打开时中文不乱码，数值与页面一致
- [ ] 诊断脚本输出的 tag 清单已提交到 `data/raw/MU/xbrl_tags.txt`
