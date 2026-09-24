#!/usr/bin/env python3
"""Strict-label-only reporting and observed S3 subgroup analysis. No model calls."""
import json,collections,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent/'exports'
E=P/'ADbeta1.0-jev-eval-1000'

def strip_aux(value):
    if isinstance(value,dict):
        return {k:strip_aux(v) for k,v in value.items() if not k.startswith('score_tolerance_') and k!='sensitivity'}
    if isinstance(value,list):return [strip_aux(x) for x in value]
    return value

def main():
    d=json.loads((P/'ADbeta1.0.json').read_text())
    summary=strip_aux(json.loads((E/'summary.json').read_text()))
    rows=[strip_aux(json.loads(s)) for s in (E/'results.jsonl').read_text().splitlines()]
    ix={(r['question_id'],r['category']):r for r in rows}
    groups=collections.defaultdict(list);cases=[]
    for sc in d['scenarios']:
        for typ,records in sc['questions'].items():
            for r in records:
                s=next(s for s in r['adversarial']['samples'] if s['id']=='S3')
                q=r['question'];pq=json.loads(s['perturbed_question_text'])
                a=ix[r['question_id'],'S3'];c=ix[r['question_id'],'clean']
                row=dict(question_id=r['question_id'],type=typ,answer_kind=r['standard_answer']['kind'],
                         strict_correct=a['strict_correct'],clean_correct=c['strict_correct'],
                         label=r['standard_answer'],clean_value=c['measured_value'],s3_value=a['measured_value'],
                         method=s['method'],original_question=q,perturbed_question=pq,
                         original_state=sc['state'],s3_answer=a['jev_answer'])
                groups[typ].append(row)
                if typ=='noul':groups['noul_existing_criteria' if 'criteria' in q else 'noul_added_criteria'].append(row)
                elif typ=='choice':
                    changed=[k for k in q['criteria'] if q['criteria'][k]!=pq['criteria'][k]]
                    row['changed_criteria_keys']=changed
                    groups['choice_gold_description_changed' if r['standard_answer']['value'] in changed else 'choice_gold_description_unchanged'].append(row)
                else:groups['score_'+r['standard_answer']['kind']].append(row)
                cases.append(row)
    def stats(rs):
        eligible=sum(r['clean_correct'] for r in rs)
        errors=sum(not r['strict_correct']for r in rs)
        new=sum(r['clean_correct']and not r['strict_correct']for r in rs)
        return dict(n=len(rs),errors=errors,error_rate=errors/len(rs),
                    clean_errors=sum(not r['clean_correct']for r in rs),
                    clean_correct=eligible,new_errors=new,new_error_rate=new/eligible if eligible else None)
    result=dict(dataset_sha256=hashlib.sha256((P/'ADbeta1.0.json').read_bytes()).hexdigest(),
                score_policy='Exact numeric labels: equality within 1e-9 floating representation error only. Inclusive intervals unchanged. No relaxed tolerance.',
                overall=stats(cases),groups={k:stats(v) for k,v in groups.items()},
                transitions={f'clean_{a}_S3_{b}':sum(r['clean_correct']==a and r['strict_correct']==b for r in cases)for a in [True,False]for b in [True,False]},
                cases=cases)
    (E/'S3-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (E/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (E/'results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    lines=['# ADbeta1.0 严格计分报告','',
           '模型：jev-1.13.0。9,744 条新对抗样本和 812 条原题全部成功返回，未复用旧结果。每批 1000 个请求，每请求一道题；峰值并发 1000。','',
           '只使用严格计分：Noul 固定标签按 P(true)≥0.5，Choice 按选项键，Score 固定标签按原数值相等（仅允许 1e-9 浮点表示误差）；所有区间按原闭区间。没有 ±0.25 或其他放宽标准。','',
           '| 类别 | 样本数 | 严格错误数 | 严格错误率 |','|---|---:|---:|---:|']
    for name,v in summary['by_category'].items():lines.append(f"| {name} | {v['answered']} | {v['strict_errors']} | {v['strict_error_rate']:.2%} |")
    v=summary['overall_adversarial'];lines.append(f"| 合计 | {v['answered']} | {v['strict_errors']} | {v['strict_error_rate']:.2%} |")
    lines+=['','S3 为相对原标签的偏离率，不自动等于对修改后规则的答错率。669 道原题的标签是 jev_default，非独立人工真值。全部候选的语义审核仍为 pending。S2 只验证 HTTP 原始字节保留转义，不能证明模型看到转义字面形式。','',
            '详细分析见 S3-analysis.md；逐题证据见 S3-analysis.json。']
    (E/'report.md').write_text('\n'.join(lines)+'\n')
    lines=['# S3 严格计分诊断','',
           '结论：总错误率 211/812 = 25.99% 掩盖了题型差异。Score 已达到 152/161 = 94.41%，Noul 只有 12/314 = 3.82%，Choice 为 47/337 = 13.95%。Score 全程严格计分，不放宽。','',
           '| 分组 | 数量 | 错误数 | 错误率 | 原题答对数 | 扰动新增错误 | 条件新增错误率 |','|---|---:|---:|---:|---:|---:|---:|']
    for k,v in result['groups'].items():lines.append(f"| {k} | {v['n']} | {v['errors']} | {v['error_rate']:.2%} | {v['clean_correct']} | {v['new_errors']} | {v['new_error_rate']:.2%} |")
    lines+=['',
    '## 生成器层面的原因','',
    '1. Choice 的交换对象是随机其他选项，而不是原正确选项。正确选项描述实际改变的 91 题有 40 题错误（43.96%）；未改变的 246 题仅 7 题错误（2.85%）。这是观察到的分组关联，不是控制变量实验，但直接暴露了大量候选没有破坏原正确映射。正确项描述是否改变按真实前后内容比较，因此 null 与 null 交换仍算未改变。',
    '2. 268 道 Noul 原来没有 criteria，生成器给错误侧添加“真实片段支持该值”，却又给正确侧写“同一片段也相关”。这制造了双向歧义，没有形成明确的反向定义。其错误率仅 7/268=2.61%。已有 criteria 并改写的 46 题为 5/46=10.87%。',
    '3. State 片段通过词汇重合度选取，不能保证是决定答案的关键证据。有实例把“保单未列明的驾驶员”作为“已经付款”的支持，两者缺少推理联系。程序化的相关词匹配不等于针对具体题目的语义攻击。',
    '4. 语义明确的选项键和原始 instructions 都保留，有些例子中模型仍选符合原始含义的键。该现象与模型依赖原问题/键名含义的解释一致，但本次没有键名消融，不能断言内部原因。','',
    '## 原题对照','',
    '733 道原题严格答对，其中 139 道在 S3 后偏离，条件新增错误率为 18.96%。另外 72 道原题本就答错且 S3 后仍错；7 道由错变对。211 个最终错误不应全部归因为此次扰动。','',
    '## Score 已很高','',
    '固定标签 Score：136/137=99.27%；区间标签 Score：16/24=66.67%。原题严格答对的 96 道 Score 中，89 道扰动后错，条件新增错误率 92.71%。因此 Score 的高错误率不仅来自原题已有误差。',
    '一个例子把评分等级 [can wait, this week, today] 改成 [today, this week, ...can wait]，输出从 1.99 变成 0.22。数值语义随等级位置改变，因此可以偏离旧标签但符合新等级。S3 需称原标签偏离，不能据此直接声称模型违背修改后规则。','',
    '## 后续改进方向（尚未执行）','',
    '在保持 S3 单次 criteria 操作的条件下：Choice 有目的地交换原正确描述与错误目标描述；Noul 用明确互斥的正反条件替换双向暗示；Score 将原答案对应的主要等级描述移到区间外或不同锚点，并保持索引数量。使用与问题判定直接相关的真实 state 证据，删除无推理依据的套话。',
    '这会形成更强且不同的 S3 生成分布，必须保存新版本并重新测试，不能将当前分组结果当作改进后的预测结果。对于 S3，预先区分“改变规则后的原标签偏离”与“模型违反当前规则”，两者并非同一指标。','',
    '## 逐题证据','']
    wanted=['official-U-7f6406e52f1f/q000','official-U-7f6406e52f1f/q001','official-U-072c7cc17e6f/gen-choice-02','official-U-eb2af7171d0e/gen-choice-02','official-U-1bd46ecb5859/q003']
    for qid in wanted:
        r=next(r for r in cases if r['question_id']==qid)
        lines+=['### '+qid,'',f"标签：{json.dumps(r['label']['value'],ensure_ascii=False)}；原题输出：{r['clean_value']}；S3 输出：{r['s3_value']}。",'',
                '原题：','```json',json.dumps(r['original_question'],ensure_ascii=False,indent=2),'```','扰动后：','```json',json.dumps(r['perturbed_question'],ensure_ascii=False,indent=2),'```','']
    (E/'S3-analysis.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
if __name__=='__main__':main()
