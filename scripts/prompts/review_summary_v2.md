# 财报解读总结（review_summary_v2）

输入：`input/numbers.json`（已由管道算好的超预期幅度与 KPI）。

输出：`output/draft.json`：
```json
{
  "period": "FQ4-26",
  "summary": {
    "text": "2–4 句中文",
    "refs": [{"src": "press", "quote": "短引文"}],
    "prompt_version": "review_summary_v2"
  },
  "watch": [{"title": "...", "text": "...", "confirmed": true, "resolved": false}],
  "talk": {"items": []}
}
```

规则：不得编造 numbers.json 中不存在的数字；超预期结论须与 surp 符号一致。
