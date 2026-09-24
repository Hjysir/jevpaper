# S3-v4 严格测试结果

仅重新调用 812 道 S3；单批并发上限 1000，实际峰值 812。模型 jev-1.13.0。原题对照使用上一轮结果，没有重新调用。
Score 采用固定值严格相等或原始闭区间，不使用放宽阈值。S3 数值表示对原标签的偏离。

| 题型 | 数量 | 旧 S3 错误数 | 旧错误率 | 新 S3 错误数 | 新错误率 |
|---|---:|---:|---:|---:|---:|
| noul | 314 | 5 | 1.59% | 159 | 50.64% |
| choice | 337 | 266 | 78.93% | 263 | 78.04% |
| score | 161 | 140 | 86.96% | 140 | 86.96% |
| 总计 | 812 | 411 | 50.62% | 562 | 69.21% |

所有 S3 均仅追加。Noul 以 A AND B 收窄或 A OR B 放宽判定边界；Choice、Score 输入与 v3 完全相同并重新调用。服务端是否合并重复键不能从 HTTP 成功推断。
其他 11 类的 8,932 条候选没有变化；旧全量评测仍对应旧 S3，本目录保存新版 S3，不能将旧报告视为新数据的全量结果。
标签来源保留，所有候选语义审核仍为 pending。S3 改变规则，对旧标签的偏离不等于违反新规则。

## Noul 边界方向与生成方法

| 分组 | 数量 | 错误数 | 错误率 |
|---|---:|---:|---:|
| broaden | 153 | 12 | 7.84% |
| label_{'metric': 'noul', 'lower': 0.4, 'upper': 0.6, 'bounds': 'inclusive'} | 2 | 2 | 100.00% |
| task_term_sufficient_condition | 61 | 9 | 14.75% |
| narrow | 161 | 147 | 91.30% |
| claim_verification | 6 | 6 | 100.00% |
| label_False | 152 | 11 | 7.24% |
| label_True | 159 | 145 | 91.19% |
| temporal_precision | 16 | 11 | 68.75% |
| label_{'metric': 'noul', 'lower': 0.4, 'upper': 0.55, 'bounds': 'inclusive'} | 1 | 1 | 100.00% |
| evidence_requirement_fallback | 48 | 42 | 87.50% |
| pilot_hand_authored | 15 | 14 | 93.33% |
| urgency_safety | 3 | 3 | 100.00% |
| request_evidence | 47 | 47 | 100.00% |
| subject_discussion_fallback | 92 | 3 | 3.26% |
| security_verification | 4 | 4 | 100.00% |
| organization_identity | 4 | 4 | 100.00% |
| identifier_format | 3 | 3 | 100.00% |
| resume_verification | 6 | 6 | 100.00% |
| extraction_explicitness | 1 | 1 | 100.00% |
| finance_precision | 2 | 2 | 100.00% |
| rule_absoluteness | 2 | 1 | 50.00% |
| tasting_verification | 1 | 1 | 100.00% |
| fruit_restriction | 3 | 2 | 66.67% |

本轮 314 道 Noul 使用任务类别规则、先前人工编写的案例定义及通用回退条件生成。收窄和放宽按原标签选择，属于已知标签的对抗构造，不是独立发现真值。语义适配仍待独立审核。Score 严格评分，所有区间保持闭区间。Choice 与 Score 输入未变化，前后返回差异来自本次重新调用。
