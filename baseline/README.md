# ref1.2 补题与五轮 Jev 基线

- 66 个 State 均原样保留；原 319 道问题定义和 ID 原样保留。
- 新增 493 个题目配对：480 道项目编写题，13 道复用官方工具路由问题定义。
- 总计 812 题：Noul 314 / Choice 337 / Score 161。每个 State 至少4/4/2，超额原题不删除。
- jev-1.13.0，每个 State 一次请求携带全部题目，重复5次；6并发，每批最多100道不同题；330请求全部成功，4060回答。
- 稳定基线标签730题；审核82题。其中运行稳定性/分布问题60题，原题适用性/定义问题28题，二者重叠6题。

## 筛选规则（项目设置，并非官方阈值）

Noul：5次均<=0.4或均>=0.6，且概率跨度<=0.10；保留均值概率及布尔判断。位于中间区间的题不自动作为正确标签。
Choice：5次同一选项，每轮该选项概率>=0.70，概率跨度<=0.10。
Score：5次最高概率等级相同，每轮最高等级概率>=0.70，连续score跨度<=0.25；保留平均score和等级，不将连续score误认为纯整数。
稳定性与正确性不同：上述标签来自Jev自身共识，不是独立gold，不能用同源标签宣称Jev真实准确率。
API confidence原样保留，未作为top-label probability使用。

## 额外审核

原日期模板中条件未成立的分支、缺失事件仍被提问，以及冰淇淋三明治原标准解释重叠，均放入审核队列，即使模型输出稳定也不直接定标。此检查仅针对已识别问题，不能宣称所有原题已完成人工质量审核。
短State硬补到10题时，题目主要覆盖显式信息、请求意图、证据充分程度；题目数量不等于10个独立能力维度。跨State共享模板保留，未伪称全是独立任务。
没有通过改写State、颠倒选项或复制同义问法补足数量。同一State新增题中未发现完全重复定义；语义质量仍可在审核页检查。

## 文件

index.html：默认显示82题审核队列，可切换全部/稳定。
dataset.json：全部State、812问题、5次结果、历史结果与来源。
labels.json / stable-labels.json / review-queue.json：标签与审查标记。
responses/：330份完整API响应；run-config.json：请求设置；label-rules.json：阈值。
input.json：运行输入快照；build.py：题目编写定义；run.py：可断点续跑；analyze.py：标签筛选；render.py：可视化生成。

官方接口依据：https://docs.typesafe.ai/api 、 https://docs.typesafe.ai/primitives/score 、 https://docs.typesafe.ai/primitives/choice
