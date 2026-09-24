# 历史数据入口

当前规范已更新为 S3-personal-opinion-v1 与 T-nonauthoritative-v1。此目录仍为更新前的完整数据快照，新版尚未生成。请勿将下述历史候选或结果当作新版评测。

`beta1.0.json` 是原题及标签。`adversarial-scenarios/001.json` 至 `066.json` 保存原场景元数据及 State；每个场景的 question_files 按原题型/原顺序引用 adversarial-questions/ 中的完整问题记录。812 个问题文件包含全部 9,744 个候选，未抽样。这样每个问题可单独检索，不必读取几十 MB 的完整文件。

`ADbeta-metadata.json` 是原 ADbeta1.0.json 除 scenarios 外的全部顶层字段。重建方法：按 scenario-index.json 顺序读场景文件，删除传输索引字段 question_files，用它引用的文件按顺序构造 questions，再放回顶层 scenarios。本次验证逐题重建后的 JSON 对象与原文件完全一致。原始字节及历史版本保存在 archives 的 core 归档中。

S2 转义和 S3 重复键均在 perturbed_question_text 字符串内保留，不要把它解析后覆盖原始字符串。所有候选语义审核仍 pending。
