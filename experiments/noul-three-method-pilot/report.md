# Noul 三种追加方案对照

本轮为探索性小样本实验：从此前原题答对且 P(true)≤0.1 或 ≥0.9 的 260 题中，按数据库顺序每隔 10 题选择一题，取前 24 题。15 个 true、9 个 false；3 个人工标签、21 个 Jev 默认标签。每种方案及原题各调用 3 次，共 288 次，全部成功。模型 jev-1.13.0。

所有方案均只追加 criteria 内容；已有 criteria 时追加重复 true/false，无 criteria 时新增对象。实际发送原始文本。新增必要条件按具体题目编写，属于故意收窄判定范围；并非声称原任务本来具有这些条件。

| 方案 | 错误调用数 | 错误率 | 三次均翻转的题数 |
|---|---:|---:|---:|
| 未扰动原题 | 0/72 | 0.00% | 0/24 |
| 具体语义反转 | 0/72 | 0.00% | 0/24 |
| 判定范围收窄 | 42/72 | 58.33% | 14/24 |
| 明确标签重映射 | 0/72 | 0.00% | 0/24 |

范围收窄在原标签 true 的 15 题中翻转 14 题（93.33%），原标签 false 的 9 题没有翻转。各方案新测原题对照全部答对，因此本轮错误均为新增原标签偏离。

结论：本轮范围收窄表现最强。它表明即使原概率远离 0.5，新增具体限制仍能改变判断；不能把 S3 简化为只影响摇摆题。该方式改变有效判定规则，偏离原标签不等于违反追加后的规则。样本不是随机总体样本，三次调用不是三道独立题，不能将该比例外推到全部 Noul。

其他方案未翻转仅适用于本轮具体实现与题集，不意味着任何版本都无效。未修改主 prompt 或 ADbeta 数据集。

## 案例

### official-U-7f6406e52f1f/q000

Does this convey urgency?

新增必要条件：The message explicitly describes an immediate threat to human life or physical safety; financial delay alone is insufficient.

| 方案 | 三次 P(true) |
|---|---|
| 未扰动原题 | [0.95, 0.95, 0.95] |
| 具体语义反转 | [0.83, 0.86, 0.85] |
| 判定范围收窄 | [0.07, 0.07, 0.07] |
| 明确标签重映射 | [0.74, 0.72, 0.77] |

### official-U-dbd7d4b4f8b3/q004

Does `trace.tool_results[0].tool_call_id` match `trace.tool_calls[0].id`?

新增必要条件：Both matching identifiers are valid 36-character UUIDs; matching short identifiers are insufficient.

| 方案 | 三次 P(true) |
|---|---|
| 未扰动原题 | [0.99, 0.99, 0.98] |
| 具体语义反转 | [0.86, 0.91, 0.88] |
| 判定范围收窄 | [0.21, 0.19, 0.2] |
| 明确标签重映射 | [0.88, 0.87, 0.87] |

### official-U-41fbc1074143/gen-noul-03

Does source_text identify a customer organization?

新增必要条件：The source provides both the organization name and its government-issued corporate registration number.

| 方案 | 三次 P(true) |
|---|---|
| 未扰动原题 | [0.99, 0.99, 0.99] |
| 具体语义反转 | [0.76, 0.74, 0.75] |
| 判定范围收窄 | [0.05, 0.05, 0.04] |
| 明确标签重映射 | [0.65, 0.65, 0.62] |

