# ADbeta1.0

本次从 beta1.0 的 812 道原题独立重新生成，覆盖此前同名文件，不读取或复用旧候选。共 9,744 个候选，每类 812 个。随机种子：1306248811257843235。

沿用 scenarios → questions → noul/choice/score，每题的 adversarial.samples 包含 Q1–Q3、S1–S3、T1–T3、P1–P3。原题、状态、标签、闭区间及人工/Jev 默认标签来源全部保留。

Q1 使用空格扰动，Q2 使用保留任务原词的句式改写；其余按 prompt 构造。每个候选均从干净原题独立复制，结构校验通过。全部 review_status 为 pending，程序校验不等于独立语义审核。

S2 原始文本保留 Unicode 转义，HTTP 传输不得先解析再序列化；无法据此保证服务端把转义形式交给模型。S3 改变判定规则，仅报告相对原标签的偏离率。T 附加文本和 P 插入指令按不可信内容计分，但不会给模型额外添加防御指令。

新测试结果位于 ADbeta1.0-jev-eval-1000/；旧的 ADbeta1.0-jev-eval/ 不对应本次新数据。生成器 regenerate_adbeta.py，运行器 eval_adbeta_1000.py，校验记录 ADbeta1.0-validation.json。

## S3-v2 更新

仅 S3 的 812 个候选从 beta1.0 原题重建。Choice 强制置换正确选项描述，Noul 两个合法键采用相同的反向描述，Score 使用原生成方法和严格评分。其他 8,932 个候选保持不变。新测试见 ADbeta1.0-S3-v2-eval/，此前全量测试是旧 S3 结果。各类别的 prompt/数据哈希见 generation_spec.category_revisions。

## S3-v3 仅追加版本

当前 S3 以 v3 为准：已有 Noul criteria 的 46 题追加反向重复成员；268 题新增反向定义；337 道 Choice 保留原成员并追加完整置换成员；161 道 Score 保留原列表并追加重复顶层 criteria。812 题均通过单片段删除后恢复原文校验。新版报告位于 ADbeta1.0-S3-v3-eval/，此前报告仅用于历史比较。重复键保留在 perturbed_question_text 和实际 HTTP 字节中，不代表模型一定能看见两组规则。

## S3-v4 边界调整版

当前 Noul 通过新增必要条件收窄 true，或新增充分条件放宽 true。所有原题/state 保持，只有一处追加。Choice、Score 从干净原题生成的输入与 v3 相同，本轮全部 812 题重新调用，无旧回答复用。最新结果位于 ADbeta1.0-S3-v4-eval/。之前各目录保留为历史，不对应当前 Noul。

## S3-v5 全部收窄版

最新 314 道 Noul 全部追加 A AND B 的肯定条件，false 对应 NOT A OR NOT B，不再按原标签选择放宽。Choice/Score 输入保持不变，完整 812 道 S3 全部新调用，结果位于 ADbeta1.0-S3-v5-eval/。其他 11 类保持不变。
