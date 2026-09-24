# Jev / 结构化决策模型安全研究材料

这是 JevSafety 项目的研究交接快照，整理日期为 2026-09-24。包含研究想法、动机、案例、基准与标签、对抗生成规范和代码、完整对抗候选、实验结果、逐请求响应、审核记录及资料来源。

## 当前规范（2026-09-24 修订）

S1 仅保留无关段落；S3 改为 question 内非权威误导观点；T1 为无关旁注，T2 为当前情境的个人解读，T3 为其他案例的主观类比。T 系列禁止伪装官方政策或核验记录。新版 S3/T 尚未生成数据或测试，仓库中的候选、脚本和结果是历史版本。

## 从哪里开始

1. [研究想法与动机](docs/01-研究想法与动机.md)：研究对象、原始表述、问题意识，以及已验证与待验证部分。
2. [数据与实验版本地图](docs/02-数据与实验版本地图.md)：原始基准、审阅候选版、ADbeta 和 S3-v2/v3/v4/v5 的对应关系。
3. [对抗框架与分析边界](docs/03-对抗框架与分析边界.md)：Q/S/T/P 的操作对象、信任边界、评分与可支持的结论。
4. [给 GPT 的检查与分析说明](GPT_CHECK_AND_ANALYZE.md)：仅说明如何检查材料、复算结果和分析证据。
5. [完整性验证](verification/verification.json)：本次交接的数据核对结果。
6. [归档与排除清单](docs/04-归档范围.md)：原始证据位置、提取方式和未重复上传的内容。

## 数据和代码入口

| 内容 | 入口 |
|---|---|
| 原题、场景、标准答案及来源 | [data/beta1.0.json](data/beta1.0.json) |
| 历史完整对抗候选 | [data/README.md](data/README.md)、[66 个场景索引](data/scenario-index.json) |
| 当前英文生成 Prompt | [materials/扰动生成prompt-en.md](materials/扰动生成prompt-en.md) |
| 最新中文攻击框架表 | [docs/03-对抗框架与分析边界.md](docs/03-对抗框架与分析边界.md) |
| 生成、S3 修订、评测与诊断代码 | [code/ref1.2](code/ref1.2) |
| 人工审核和对抗工作台代码 | [code/jev-bench](code/jev-bench) |
| 实验目录索引 | [experiments/index.json](experiments/index.json) |
| 第一轮全量结果 | [experiments/ADbeta1.0-jev-eval-1000/report.md](experiments/ADbeta1.0-jev-eval-1000/report.md) |
| 历史 S3-v5 结果 | [experiments/ADbeta1.0-S3-v5-eval/report.md](experiments/ADbeta1.0-S3-v5-eval/report.md) |
| 两版演示文稿、逐页文字及案例 | [materials](materials) |
| 人工审核历史、工作台尝试 | [review-history](review-history) |
| 原文件与逐请求响应 | [archives](archives)、[逐文件索引](provenance/archive-file-manifest.jsonl) |

## 当前快照的事实

- 原题：66 个场景，812 道题；Noul 314、Choice 337、Score 161。
- 原题标签来源：143 条 human_review，669 条 jev_default；不是全部人工独立金标准。
- 历史快照对抗候选：9,744 条，12 个子类各 812 条；候选语义审核全部 pending。
- 首次全量评测：812 条 clean + 9,744 条候选，10,556 条结果。该轮 S3 是历史版本。
- 历史 S3-v5：单独重新调用 812 条；548 条偏离原标签。S3 改动规则，偏离不等于违反修改后的规则。
- 本仓库整理没有新增模型调用，没有改变原题、标签、扰动样本和历史结果。

原始文档可能包含旧数字、过时说明和未证实主张。请通过版本地图、哈希及逐条结果核对，不要以文件名中的“最新”或单份汇总替代证据。
