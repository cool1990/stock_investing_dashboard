# P1 验收对照（04 §7）

本地预览：[财务报表](http://127.0.0.1:43123/stock_investing_dashboard/#/MU/financials)

| 清单项 | 状态 | 说明 |
|---|---|---|
| FQ4-26 利润表：营收 54,229、净利润 37,701、摊薄 EPS 32.87；Non-GAAP EPS 33.42 | ✅ | GAAP / Non-GAAP EPS 来自 `overrides.financials.FQ4-26`（companyfacts 尚无 FY2026 10-K，`max end=2026-05-28`）。10-K 入库后可去掉覆盖。 |
| FQ4-26 单季经营现金流 43,973 = 89,675 − 45,702 | ✅ | `ytd.cfo` / Q3 YTD 与公式一致；pytest 覆盖 |
| 以 FY2023 为基数的同比显示 n.m. | ✅ | FY2024 净利润同比 `n.m.`（FY23 NI = −5,833） |
| 环比在累计和年度视图下禁用 | ✅ | 页面 JSON 中 ytd/y 的 `qoq=null`；前端 `aria-disabled` + 透明度 0.45 |
| 「全部」范围横向滚动、第一列固定 | ✅ | `table-wrap--sticky` |
| 导出 CSV UTF-8 BOM、与当前视图一致 | ✅ | `\uFEFF` + 文件名 `MU_利润表_单季_YYYY-MM-DD.csv` |
| `data/raw/MU/xbrl_tags.txt` 已提交 | ✅ | 629 tags |

## StockHeader

| 字段 | 状态 |
|---|---|
| 股价 / 1D / YTD | ✅ Yahoo closes |
| 市值 | ✅ 股价 × sharesOutstanding |
| 净现金 / EV | ✅ 最近一期完整 BS（目前 FQ3-26）推算 |
| 下次财报 | ✅ Yahoo calendar（若有） |
| Forward PE / 做空等 | ⏳ 后续阶段 |

## 测试

```bash
python3 -m pytest   # 11 passed（含 P1 financials）
cd web && npm test  # fmt vitest
```
