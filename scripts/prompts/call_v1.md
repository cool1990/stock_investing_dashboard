# 电话会要点提取（call_v1）

输入：`input/review_numbers.json`、可选准备稿/文字稿。

输出：`output/draft.json`，符合 `schema.json`。

规则：
1. 中文要点；每条带 `src`（页码或时间戳）。
2. 准备稿缺失时标注「准备稿未获取」，不得把第三方文字稿当作官方准备稿。
3. 区分「业绩回顾」与「未来展望」；变化处打 tag「变化」并写 prev。
4. 禁止编造数字；数字须来自 input 或原文引用。
