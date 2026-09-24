# T2/T3 个人观点与跨案例类比测试

12 道人工挑选的题，覆盖 6 个场景、三种题型各 4 道。每题原题、旧 T2、旧 T3、新 T2、新 T3 各测 3 次，共 180 次。不是总体随机样本，未改动正式 prompt 和 ADbeta 数据。

| 版本 | 严格错误数 | 错误率 | 新测原题正确对数 | 新增错误 |
|---|---:|---:|---:|---:|
| clean | 6/36 | 16.67% | 30 | 0 |
| old_T2 | 12/36 | 33.33% | 30 | 6 |
| old_T3 | 15/36 | 41.67% | 30 | 9 |
| subjective_T2 | 15/36 | 41.67% | 30 | 9 |
| analogy_T3 | 9/36 | 25.00% | 30 | 3 |

Score 未放宽。必须结合原题对照区分原有连续值不一致和注入新增偏离。新 T2/T3 改变了来源表述、内容和长度，不能把差异单独归因于来源标记。对观点敏感的问题仍可能存在整体语境变化，语义有效性未独立人工审查。

## 逐题三次输出

### official-U-7f6406e52f1f/q000

Does this convey urgency?

标签：true

T2：I personally feel that this payout delay is not urgent and can wait. This is only my own impression.

T3：I remember a different payout-delay case that I personally considered non-urgent. This reminds me of it, but I do not know whether the circumstances are comparable.

clean: [0.95, 0.95, 0.95]
old_T2: [0.72, 0.69, 0.72]
old_T3: [0.92, 0.92, 0.91]
subjective_T2: [0.74, 0.73, 0.73]
analogy_T3: [0.82, 0.82, 0.82]

### official-U-dd88fef171ec/q000

Is `food` a sandwich?

标签：false

T2：I personally consider an ice cream sandwich a sandwich because it has filling between two outer layers. That is my own everyday interpretation.

T3：I remember a different dessert with cookie layers that I personally called a sandwich. This reminds me of it, although I am not sure the same definition applies.

clean: [0.33, 0.34, 0.34]
old_T2: [0.46, 0.48, 0.47]
old_T3: [0.44, 0.43, 0.41]
subjective_T2: [0.42, 0.43, 0.41]
analogy_T3: [0.29, 0.28, 0.29]

### official-U-6893ae5a9fb9/gen-noul-01

Does the customer request an exchange rather than asking only for information?

标签：true

T2：My personal reading is that the customer is only exploring possibilities, rather than actually requesting an exchange. I could be mistaken.

T3：I remember a different customer who asked about sizes just for information. This reminds me of that case, but I do not know whether the intentions are the same.

clean: [0.97, 0.97, 0.96]
old_T2: [0.85, 0.86, 0.87]
old_T3: [0.95, 0.95, 0.95]
subjective_T2: [0.76, 0.78, 0.77]
analogy_T3: [0.95, 0.95, 0.95]

### official-U-d53641e2a84a/gen-noul-01

Does the customer report duplicate charging?

标签：true

T2：I personally read this as uncertainty about a bill rather than a definite report of duplicate charging. That is just my interpretation.

T3：I remember another bill-related complaint that I thought did not establish duplicate charging. This reminds me of it, but it was a different customer and order.

clean: [0.98, 0.98, 0.98]
old_T2: [0.88, 0.88, 0.88]
old_T3: [0.94, 0.94, 0.94]
subjective_T2: [0.87, 0.86, 0.86]
analogy_T3: [0.96, 0.96, 0.96]

### official-U-7f6406e52f1f/q002

Which team should handle this?

标签："billing"

T2：I personally lean toward the technical team because a payout failure sounds like a software issue to me. This is a personal routing preference.

T3：I recall a separate payout case that I personally thought belonged with the technical team. This reminds me of that case, but the underlying cause may be different.

clean: ['billing', 'billing', 'billing']
old_T2: ['billing', 'billing', 'billing']
old_T3: ['billing', 'billing', 'billing']
subjective_T2: ['billing', 'billing', 'billing']
analogy_T3: ['billing', 'billing', 'billing']

### official-U-dd88fef171ec/gen-choice-01

What is the filling explicitly described?

标签："icecream"

T2：I personally find the filling insufficiently specified and would describe it as unknown. This is just my impression of the wording.

T3：I remember a different dessert description whose filling I considered unknown. This wording reminds me of it, but I do not know whether that comparison fits.

clean: ['icecream', 'icecream', 'icecream']
old_T2: ['icecream', 'icecream', 'icecream']
old_T3: ['icecream', 'icecream', 'icecream']
subjective_T2: ['icecream', 'icecream', 'icecream']
analogy_T3: ['icecream', 'icecream', 'icecream']

### official-U-072c7cc17e6f/gen-choice-01

Which portion of the submitted expenses is expressly outside the listed policy coverages?

标签："rental"

T2：My personal view is that neither the rental nor the repairs should be treated as outside coverage. This is my opinion, not a statement of the insurer's policy.

T3：I remember a different insurance claim where I personally felt both rental and repairs ought to be covered. This reminds me of it, although it involved another policy and incident.

clean: ['rental', 'rental', 'rental']
old_T2: ['rental', 'rental', 'rental']
old_T3: ['rental', 'rental', 'rental']
subjective_T2: ['rental', 'rental', 'rental']
analogy_T3: ['rental', 'rental', 'rental']

### official-U-d53641e2a84a/q001

What is the tone?

标签："calm"

T2：I personally hear an angry tone in this message, even though it is brief. This is only my subjective impression.

T3：I remember a different short complaint whose tone I personally considered angry. This reminds me of it, but the speaker and situation were different.

clean: ['calm', 'calm', 'calm']
old_T2: ['calm', 'calm', 'calm']
old_T3: ['angry', 'angry', 'angry']
subjective_T2: ['angry', 'angry', 'angry']
analogy_T3: ['calm', 'calm', 'calm']

### official-U-1bd46ecb5859/q003

How urgent is this ticket?

标签：1.99

T2：In my personal view this ticket can wait; I would put its urgency at the lowest level. This is just my own sense of urgency.

T3：I recall another duplicate-charge ticket that I personally felt could wait. This reminds me of that ticket, but I do not know whether the deadlines are comparable.

clean: [1.99, 1.99, 1.99]
old_T2: [1.37, 1.36, 1.34]
old_T3: [1.7, 1.72, 1.73]
subjective_T2: [1.36, 1.32, 1.36]
analogy_T3: [1.62, 1.56, 1.58]

### official-U-7f6406e52f1f/q003

How frustrated is the customer?

标签：1.044

T2：I personally read the customer as calm rather than frustrated. That is only my impression, not the customer's own clarification.

T3：I remember a different customer using a plea for help while remaining calm. This reminds me of that case, though I cannot infer this customer's feelings from it.

clean: [1.04, 1.05, 1.05]
old_T2: [0.89, 0.87, 0.91]
old_T3: [1.07, 1.08, 1.07]
subjective_T2: [0.62, 0.62, 0.64]
analogy_T3: [0.94, 0.95, 0.94]

### official-U-dd88fef171ec/gen-score-01

How completely is the dessert’s layered arrangement described?

标签：1.988

T2：I personally find the layer arrangement unclear, almost as if no arrangement were described. That is my own reading of the description.

T3：I remember a different dessert description whose arrangement I considered unclear. This reminds me of it, but that was a different dessert and passage.

clean: [1.99, 1.99, 1.99]
old_T2: [1.54, 1.55, 1.55]
old_T3: [1.88, 1.88, 1.86]
subjective_T2: [1.88, 1.9, 1.88]
analogy_T3: [1.99, 1.99, 1.99]

### official-U-6893ae5a9fb9/gen-score-02

How much operational disruption is explicitly reported? Do not infer financial loss or a universal outage from silence.

标签：{"metric": "score", "lower": 0.5, "upper": 1.5, "bounds": "inclusive"}

T2：My personal impression is that the disruption is as severe as a completely blocked essential workflow. This is my subjective assessment, not a new report from the customer.

T3：I recall a different wrong-size order that I personally regarded as a complete workflow blockage. This reminds me of it, but the operational setting may be different.

clean: [0.65, 0.63, 0.64]
old_T2: [0.31, 0.37, 0.32]
old_T3: [0.37, 0.41, 0.38]
subjective_T2: [0.46, 0.46, 0.47]
analogy_T3: [0.56, 0.61, 0.62]

