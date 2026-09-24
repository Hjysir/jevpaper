# 原始研究证据归档

index.json 指定 5 个 tar.xz 归档的分卷顺序、大小与 SHA-256。分卷只是传输格式，不是数据抽样。每个分卷最多 4 MiB。

在下载完整仓库后，先校验并合并：

```sh
python3 archives/restore_archives.py --output /your/new/output/directory
```

该命令只合并归档，不调用模型、不执行归档中的代码。使用 `--extract` 可在输出目录下的 extracted/ 解压；使用 `--archive 01-core-benchmark-and-experiments.tar.xz` 可只处理一个归档。需要直接阅读数据时优先使用 ../data 和 ../experiments 的文本文件。

原始文件清单见 ../provenance/archive-file-manifest.jsonl。上游资料索引含部分未复制的原镜像路径，范围说明见 ../docs/04-归档范围.md。
