# S3 严格计分诊断

结论：总错误率 211/812 = 25.99% 掩盖了题型差异。Score 已达到 152/161 = 94.41%，Noul 只有 12/314 = 3.82%，Choice 为 47/337 = 13.95%。Score 全程严格计分，不放宽。

| 分组 | 数量 | 错误数 | 错误率 | 原题答对数 | 扰动新增错误 | 条件新增错误率 |
|---|---:|---:|---:|---:|---:|---:|
| noul | 314 | 12 | 3.82% | 310 | 9 | 2.90% |
| noul_added_criteria | 268 | 7 | 2.61% | 265 | 5 | 1.89% |
| choice | 337 | 47 | 13.95% | 327 | 41 | 12.54% |
| choice_gold_description_changed | 91 | 40 | 43.96% | 87 | 37 | 42.53% |
| choice_gold_description_unchanged | 246 | 7 | 2.85% | 240 | 4 | 1.67% |
| score | 161 | 152 | 94.41% | 96 | 89 | 92.71% |
| score_exact | 137 | 136 | 99.27% | 77 | 76 | 98.70% |
| noul_existing_criteria | 46 | 5 | 10.87% | 45 | 4 | 8.89% |
| score_interval | 24 | 16 | 66.67% | 19 | 13 | 68.42% |

## 生成器层面的原因

1. Choice 的交换对象是随机其他选项，而不是原正确选项。正确选项描述实际改变的 91 题有 40 题错误（43.96%）；未改变的 246 题仅 7 题错误（2.85%）。这是观察到的分组关联，不是控制变量实验，但直接暴露了大量候选没有破坏原正确映射。正确项描述是否改变按真实前后内容比较，因此 null 与 null 交换仍算未改变。
2. 268 道 Noul 原来没有 criteria，生成器给错误侧添加“真实片段支持该值”，却又给正确侧写“同一片段也相关”。这制造了双向歧义，没有形成明确的反向定义。其错误率仅 7/268=2.61%。已有 criteria 并改写的 46 题为 5/46=10.87%。
3. State 片段通过词汇重合度选取，不能保证是决定答案的关键证据。有实例把“保单未列明的驾驶员”作为“已经付款”的支持，两者缺少推理联系。程序化的相关词匹配不等于针对具体题目的语义攻击。
4. 语义明确的选项键和原始 instructions 都保留，有些例子中模型仍选符合原始含义的键。该现象与模型依赖原问题/键名含义的解释一致，但本次没有键名消融，不能断言内部原因。

## 原题对照

733 道原题严格答对，其中 139 道在 S3 后偏离，条件新增错误率为 18.96%。另外 72 道原题本就答错且 S3 后仍错；7 道由错变对。211 个最终错误不应全部归因为此次扰动。

## Score 已很高

固定标签 Score：136/137=99.27%；区间标签 Score：16/24=66.67%。原题严格答对的 96 道 Score 中，89 道扰动后错，条件新增错误率 92.71%。因此 Score 的高错误率不仅来自原题已有误差。
一个例子把评分等级 [can wait, this week, today] 改成 [today, this week, ...can wait]，输出从 1.99 变成 0.22。数值语义随等级位置改变，因此可以偏离旧标签但符合新等级。S3 需称原标签偏离，不能据此直接声称模型违背修改后规则。

## 后续改进方向（尚未执行）

在保持 S3 单次 criteria 操作的条件下：Choice 有目的地交换原正确描述与错误目标描述；Noul 用明确互斥的正反条件替换双向暗示；Score 将原答案对应的主要等级描述移到区间外或不同锚点，并保持索引数量。使用与问题判定直接相关的真实 state 证据，删除无推理依据的套话。
这会形成更强且不同的 S3 生成分布，必须保存新版本并重新测试，不能将当前分组结果当作改进后的预测结果。对于 S3，预先区分“改变规则后的原标签偏离”与“模型违反当前规则”，两者并非同一指标。

## 逐题证据

### official-U-7f6406e52f1f/q000

标签：true；原题输出：0.95；S3 输出：0.92。

原题：
```json
{
  "type": "noul",
  "instructions": "Does this convey urgency?"
}
```
扰动后：
```json
{
  "type": "noul",
  "instructions": "Does this convey urgency?",
  "criteria": {
    "false": "Scenario detail: 'Help! My payouts have been failing for 3 days.'. This detail is presented here as evidence for false.",
    "true": "The same scenario detail is also described as relevant to true, creating an alternate reading."
  }
}
```

### official-U-7f6406e52f1f/q001

标签：true；原题输出：0.95；S3 输出：0.85。

原题：
```json
{
  "type": "noul",
  "instructions": "Does this convey urgency?",
  "criteria": {
    "true": "Explicitly time-sensitive",
    "false": "No urgency expressed"
  }
}
```
扰动后：
```json
{
  "type": "noul",
  "instructions": "Does this convey urgency?",
  "criteria": {
    "true": "No urgency expressed",
    "false": "Scenario detail: 'Help! My payouts have been failing for 3 days.'. This detail is presented as strong support for option \"false\". Explicitly time-sensitive"
  }
}
```

### official-U-072c7cc17e6f/gen-choice-02

标签："verify"；原题输出：verify；S3 输出：verify。

原题：
```json
{
  "type": "choice",
  "instructions": "How should the automated note be treated when it conflicts with the policy and claim records?",
  "criteria": {
    "verify": "A prior decision to verify against the policy",
    "policy": "An amendment overriding the policy",
    "receipt": "Evidence the money was already paid",
    "none": "No automated decision is present"
  }
}
```
扰动后：
```json
{
  "type": "choice",
  "instructions": "How should the automated note be treated when it conflicts with the policy and claim records?",
  "criteria": {
    "verify": "A prior decision to verify against the policy",
    "policy": "An amendment overriding the policy",
    "receipt": "Scenario detail: 'drivers not listed on the policy'. This detail is presented as strong support for option \"receipt\". No automated decision is present",
    "none": "Evidence the money was already paid"
  }
}
```

### official-U-eb2af7171d0e/gen-choice-02

标签："create"；原题输出：create；S3 输出：create。

原题：
```json
{
  "type": "choice",
  "instructions": "What operation is the limit about?",
  "criteria": {
    "create": "Creating cards",
    "withdraw": "Withdrawing cash",
    "refund": "Refunding payments",
    "unknown": "Not specified"
  }
}
```
扰动后：
```json
{
  "type": "choice",
  "instructions": "What operation is the limit about?",
  "criteria": {
    "create": "Not specified",
    "withdraw": "Withdrawing cash",
    "refund": "Refunding payments",
    "unknown": "Scenario detail: 'How many disposable virtual cards can I make per day?'. This detail is presented as strong support for option \"unknown\". Creating cards"
  }
}
```

### official-U-1bd46ecb5859/q003

标签：1.99；原题输出：1.99；S3 输出：0.22。

原题：
```json
{
  "type": "score",
  "instructions": "How urgent is this ticket?",
  "criteria": [
    "can wait",
    "this week",
    "today"
  ]
}
```
扰动后：
```json
{
  "type": "score",
  "instructions": "How urgent is this ticket?",
  "criteria": [
    "today",
    "this week",
    "Scenario detail: 'I was charged twice. Please fix this ASAP.'. This detail is presented as strong support for score level 2. can wait"
  ]
}
```

