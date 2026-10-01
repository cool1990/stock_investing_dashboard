# P0 与设计稿差异（静态样例阶段）

## 全站

- 默认路由为 `#/` 观察池；顶栏搜索回车进入 `#/TICKER`（财报解读），非共识页。
- StockTabs 使用 `review|financials|call|consensus|price`；兼容 `overview`→`review`、`statements`→`financials`。
- 多数行情、市值、Forward PE、观察池 KPI 数字在样例 JSON 中为 `null`，页面显示 `[ ]`。
- **共识页**部分表格/增速仍用前端 `signed-text` 配色（`colorForSignedText`），其他页优先用 JSON `*_tone`（`up/down/flat/na`）。

## 观察池

- 表头排序、列选择（localStorage）、`.ics` 导出、红色规则 YAML 动态文案未实现。
- 搜索框在观察池仅做前缀过滤，不回车跳转。

## 财报解读

- 期间下拉（历史 FQ）未做；仅展示当前 `period`。
- 拆解区柱状/折线为简化 div 柱，非设计稿 SVG 叠加与 400% 封顶。
- 9 指标条仅渲染样例中存在的 `metrics` 键（rev/gm/eps），非完整 9 项。
- 主卡选中与拆解指标 Segmented 联动部分实现。

## 财务报表

- 样例仅 5 列；范围切换 UI 有，列数少时与「全部」等价。
- `ytd` 在资产负债表/权益表为空对象时显示占位文案。
- 行类型 `d/s/i` 样式部分还原；无 yoy_tone 来自后端（子行颜色为默认墨色）。

## 电话会

- 左侧历史列表仅当前一场；无 sticky 双栏完整 20 场列表。
- 无「相对上一场」总开关；`prev` 字段在要点上直接展示。
- 原文来源 Segmented 对样例 `official/remarks` 字符串列表适配；准备稿缺失时 banner 提示。

## 股价反应

- 窗口 Segmented 未驱动 KPI 标题联动（三窗 KPI 同时展示）。
- `series` 为空时走势图/散点显示占位；无十字线、回归 R²。
- 复盘表列较设计稿精简。

## 分析师预期

- 保持既有实现；与设计稿一致度最高。

## 数据说明

- 运行状态来自样例 `rows[].status`，非实时 `_status.json` 拉取。
