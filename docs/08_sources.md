# 08 数据说明（全站）

- 路由：`#/sources`（AppHeader 的「数据说明」入口）
- 设计稿：`docs/design/sources-mockup.dc.html`
- 通用约定：`01_common.md`

## 1. 目的

让用户知道每个数字的三件事：**从哪里来、有多可靠、拿不到时会怎么显示**。同时展示各数据源最近的运行状态，方便排查问题。

## 2. 页面结构

```
AppHeader（「数据说明」高亮），无 StockHeader

数据说明
每个数字从哪里来、有多可靠、拿不到时怎么显示。原则：数字只来自结构化来源或规则解析；
AI 只做文本理解并附原文；缺数据就留空或写「不可得」，不拿另一个来源的数默默补上。

图例： [稳定] 官方、结构化，几乎不变   [有条件] 非官方接口、推算或需要自建积累   [不稳定] AI 生成或网页抓取，易变，必须附原文

┌数据 | 可靠性 | 来源 | 更新 | 缺失时 | 运行状态（新增）──────────────────────────┐
│三大报表（GAAP）            [稳定]   SEC EDGAR XBRL…   10-Q/10-K 提交后  留空…  ● 正常 10-01 06:41 │
│  用于：财务报表 · 分项拆解（小字）                                              │
│…                                                                               │
└────────────────────────────────────────────────────────────────────────────────┘
┌显示约定──────────────────────────────────────────────────────────────────────┐
│ 颜色 / 口径 / 同比环比 / 历史回填（4 条）                                      │
└──────────────────────────────────────────────────────────────────────────────┘
页脚：本页由 config/sources.yaml 生成，新增数据源时同步更新。
```

### 2.1 可靠性徽章

| 徽章 | 样式 | 含义 |
|---|---|---|
| 稳定 | `--ok-bg` / `--ok-ink` | 官方、结构化，几乎不变 |
| 有条件 | `--mid-bg` / `--mid-ink` | 非官方接口、推算或需要自建积累 |
| 不稳定 | `--bad-bg` / `--bad-ink` | AI 生成或网页抓取，易变，必须附原文 |

徽章是圆角胶囊，11px，字重 500。

### 2.2 数据源表

- **数据列**：第一行是数据名（加粗）；第二行是「用于：页面 · 区块」（小字，`--muted`）。
- **运行状态列**（新增，设计稿中没有）：
  - 根据 `_status.json` 显示：● 正常（蓝色）加最近成功时间；或 ● 失败（橙色）加最近失败时间，`title` 中显示错误信息；
  - 超过预期更新周期 2 倍仍未成功时，显示 ● 过期（琥珀色）。
- 表格在 < 900px 时横向滚动。

### 2.3 显示约定（4 条）

1. **颜色**：蓝 = 增加 / 好于预期，橙 = 减少 / 差于预期，灰 = 无数据。全站统一，不使用红绿。
2. **口径**：美光为非自然年财年（截至 8 月底 / 9 月初），期间写作 FQ4-26；比较同行时按期末日期对齐。
3. **同比 / 环比**：金额用 %，比率用 pp；基数 ≤ 0 时显示 n.m.；缺少基数时显示「—」。
4. **历史回填**：统一从期末落在自然年 2021Q4 的财季开始。

## 3. `config/sources.yaml`（初始内容）

注意：共识的主来源以 `06_consensus.md` 为准，即 **Yahoo 为主、Nasdaq 交叉校验**，这一点与设计稿不同。

```yaml
- id: xbrl
  name: 三大报表（GAAP）
  used: 财务报表 · 分项拆解
  reliability: 稳定
  source: SEC EDGAR XBRL（companyfacts），免费、无需密钥
  freq: 10-Q / 10-K 提交后
  missing: 留空；不从第三方补
  status_keys: [edgar_xbrl]
  expected_hours: 2400
- id: press
  name: Non-GAAP、分部、指引
  used: 财报解读
  reliability: 稳定
  source: 8-K 附件 EX-99.1 新闻稿，规则解析 + 数字反查
  freq: 发布当日
  missing: 标「未披露」
  status_keys: [edgar_press]
- id: q_flow
  name: 单季流量科目
  used: 财务报表
  reliability: 有条件
  source: 由 10-Q 年初至今累计数相减；Q4 = 全年 − 前三季
  freq: 季度
  missing: 相减失败的格子留空
- id: remarks
  name: 管理层准备稿
  used: 电话会 · 表述变化
  reliability: 稳定
  source: 公司 IR 网站 Prepared Remarks PDF
  freq: 发布当日
  missing: 准备稿未获取；原文 tab 可切换到第三方文字稿，但必须明确标注来源，不得静默顶替官方准备稿
- id: qa
  name: 电话会问答
  used: 电话会 · 分析师问题
  reliability: 有条件
  source: 第三方公开文字稿；官网 webcast 回放作校对
  freq: T+1 内
  missing: 标「原文解析中 / 无逐字稿」
- id: ai_text
  name: 表述变化、问题聚类、原因
  used: 财报解读 · 电话会
  reliability: 不稳定
  source: AI 生成（默认在 Cursor 中处理任务包，预留 DeepSeek API），每条附原句与出处，prompt 带版本号，经脚本校验
  freq: 每次财报
  missing: 写「管理层未解释」，不推测
- id: consensus
  name: 一致预期（EPS、收入）
  used: 分析师预期 · 财报解读 · 观察池
  reliability: 有条件
  source: Yahoo（yfinance）为主，Nasdaq 公开接口交叉校验，MarketBeat / yfinance 历史回填
  freq: 每日快照
  missing: 两源差异 > 3% 标黄；缺失写「无一致预期」
- id: revisions
  name: 预期修正轨迹
  used: 分析师预期 · 观察池
  reliability: 有条件
  source: 自建每日快照（上线日起积累）；早期用 Yahoo EPS Trend 的 7/30/60/90 天点
  freq: 每日
  missing: 写「不可得」，不伪造上调 / 下调家数
- id: prices
  name: 股价、市值、股本
  used: 观察池 · 基础信息 · 股价反应
  reliability: 有条件
  source: yfinance（Yahoo），备份 Stooq 日线
  freq: 每日收盘后
  missing: 显示上一次快照并标时间
- id: intraday
  name: 盘后 / 盘前价格
  used: 股价反应
  reliability: 有条件
  source: yfinance 分钟线，仅能回溯约 30–60 天，需在财报日当晚快照
  freq: 财报日
  missing: 历史用次日开盘跳空近似
- id: iv
  name: 期权隐含波动
  used: 基础信息 · 股价反应
  reliability: 不稳定
  source: yfinance 期权链，发布前一日快照
  freq: 财报前一日
  missing: 留空
- id: short
  name: 做空比例
  used: 观察池 · 基础信息
  reliability: 有条件
  source: FINRA 半月披露（经 yfinance 获取）
  freq: 每月两次
  missing: 显示最近一期并标日期
- id: filings
  name: 公告与内部人交易
  used: 观察池
  reliability: 稳定
  source: EDGAR 8-K、Form 4（复用现有公告抓取任务）
  freq: 每日
  missing: —
```

`status_keys` 把每一项和 `_status.json` 中的一个或多个来源键关联起来；`expected_hours` 用于判断「过期」。没有填写的项，按 `freq` 推算一个默认值。

## 4. 数据模型 `data/pages/sources.json`

由 `build_sources.py` 合并 `sources.yaml` 与 `_status.json` 生成：

```json
{ "intro": "…", "legend": [{"k":"稳定","desc":"官方、结构化，几乎不变"}],
  "rows": [{"id":"xbrl","name":"三大报表（GAAP）","used":"…","reliability":"稳定","source":"…","freq":"…","missing":"…",
            "status":{"state":"ok|fail|stale","last_ok":"2026-10-01T22:41Z","last_err":null,"err_msg":null}}],
  "conventions": ["…","…","…","…"] }
```

## 5. 注意事项

1. 页面上的所有文字都来自 `sources.yaml` 和本文件，**不要写死在前端**。新增数据源时，只改 YAML。
2. 运行状态的时间按北京时间显示。
3. 失败信息中可能包含 URL 或堆栈，展示前要截断到 200 字，并去掉任何像密钥的内容（例如 `sk-` 开头的字符串）。

## 6. 验收清单

- [ ] 13 行数据源全部显示，徽章颜色正确
- [ ] 人为让 yfinance 抓取失败后，「股价」行显示 ● 失败和错误摘要，其他页面仍显示旧数据
- [ ] 在 `sources.yaml` 中新增一行，重新构建后页面出现新行，不需要改前端
