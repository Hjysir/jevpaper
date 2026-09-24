# Choice notice/new_criteria 最小对照

冰淇淋夹心题，原标签 icecream。每组重复 3 次，规则文本相同。包装位于原 criteria 内，原选项全部保留。正式 prompt 和数据库未改动。

| 组别 | HTTP | 选择结果 | 原标签错误数 |
|---|---|---|---|
| clean | [200, 200, 200] | ['icecream', 'icecream', 'icecream'] | 0/3 |
| direct_duplicate | [200, 200, 200] | ['unknown', 'unknown', 'unknown'] | 3/3 |
| notice | [200, 200, 200] | ['icecream', 'icecream', 'icecream'] | 0/3 |
| new_criteria | [200, 200, 200] | ['icecream', 'icecream', 'icecream'] | 0/3 |

注意：Choice 的 criteria 顶层成员名可能成为输出选项。notice/new_criteria 包装不一定是中性元数据；应检查返回 probabilities 是否新增同名候选。该实验仅覆盖这道题和该嵌套位置。
