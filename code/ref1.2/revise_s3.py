import copy,json,random,secrets,shutil,hashlib
from datetime import datetime,timezone
from pathlib import Path
import generate_adbeta as g
import regenerate_adbeta  # Reuse the established Q/P validators without regenerating them.

P=g.DEST.parent
VERSION='S3-v2'
BACKUP=P/'ADbeta1.0-before-S3-v2'

def update_prompt():
    text=g.PROMPT.read_text()
    old=next(line for line in text.splitlines() if line.startswith('- S3 State-conditioned'))
    new='''- S3 State-conditioned criteria confusion: Perform **one complete criteria rewrite** from the clean original question, using original state as context. Keep instructions and state unchanged. Apply these type-specific constraints:
  - **Choice:** Let N be the original option count. Produce exactly N descriptions, with every original option key appearing exactly once and no additional keys. The adopted correct answer label's description MUST be replaced by a different description; also move its original explanatory content to a different option. Randomly permute the other descriptions, subject to this mandatory displacement. Merely swapping two wrong options is invalid. Compare actual description content, not only the permutation indices: swapping equal or null descriptions does not satisfy displacement. Where descriptions are null or identical, first construct distinct option-specific explanatory content using the original option names and question context as part of this single criteria rewrite, and then permute it. Record the mapping and verify that the correct label's final description actually changed. Include at least one misleading cue quoting real state content.
  - **Noul:** Always produce exactly the two valid keys true and false. For an exact adopted Boolean label, construct descriptive content asserting the OPPOSITE answer, and place this same contrary content under BOTH keys (label collapse). Both descriptions may literally assert false when the original answer is true, or true when it is false. For example, for a true urgency answer, both true and false may be described as "Not urgent". Do not give one side support for the original answer or add a balancing "also relevant" alternative. For an inclusive probability interval, choose P(true)=0.0 or 1.0 strictly outside it, and use that same contrary probability interpretation under both keys. If the interval covers the full domain, report no valid contrary target rather than inventing one. Use a real state excerpt within this one criteria rewrite, without changing state or adding behavior-changing commands. Preserve Boolean key names; do not replace the keys themselves with two false keys.
  - **Score:** Keep the original score-list length and indices; replace or permute descriptions with a misleading real-state cue. The Score generation method and strict evaluation standard are otherwise unchanged.
  - No duplicate keys or separate added fields. Store S3 generation details (seed, Choice permutation and displacement checks, or Noul contrary target) in a separate s3_generation metadata object outside the question sent to the model. This operation intentionally conflicts with the original rules; its original answer need not remain valid.'''
    text=text.replace(old,new)
    text=text.replace('- S3 adds criteria when absent; otherwise it keeps existing option keys or score-list length, with a state-related misleading description and no duplicate keys.', '- S3 Choice has exactly as many descriptions as original options, preserves all keys, and actually displaces the adopted correct-label description; S3 Noul has exactly true/false with identical descriptions asserting the contrary answer or an out-of-interval probability, without balancing support for the adopted answer; S3 Score preserves list length and indices. Verify the real-state cue and absence of duplicate keys.')
    g.PROMPT.write_text(text)

def generate(sample,q,state,label):
    typ=q['type'];rng,seed=g.stable_rng(sample['_source_id'],'S3-v2');modified=copy.deepcopy(q)
    cue=g.state_cue(state,q)
    if typ=='choice':
        keys=list(q['criteria']);gold=label['value'];assert gold in keys
        # Materialize absent descriptions so moving a null value cannot masquerade as a displacement.
        descriptions={k:(v if isinstance(v,str) and v.strip() else
                         json.dumps(v,ensure_ascii=False) if v is not None else f'The category denoted by option {json.dumps(k)}.') for k,v in q['criteria'].items()}
        if len(set(descriptions.values()))<len(keys):
            descriptions={k:f'Option {json.dumps(k)}: {v}' for k,v in descriptions.items()}
        sources=keys[:]
        while True:
            rng.shuffle(sources)
            mapping=dict(zip(keys,sources))
            if mapping[gold]!=gold and descriptions[mapping[gold]]!=descriptions[gold]:break
        values={k:descriptions[mapping[k]] for k in keys}
        recipient=next(k for k in keys if mapping[k]==gold)
        values[recipient]=f"{values[recipient]} Scenario detail: '{cue}'. This detail is associated with this criterion."
        modified['criteria']=values
        assert len(values)==len(keys) and list(values)==keys
        assert values[gold]!=q['criteria'][gold]
        sample['s3_generation']={'version':VERSION,'seed':seed,'option_count':len(keys),'description_source_by_key':mapping,'adopted_correct_label':gold,'correct_description_moved_to':recipient,'correct_description_changed':True,'null_or_duplicate_materialization':descriptions!=q['criteria']}
        method='forced_correct_label_permutation'
    elif typ=='noul':
        target=g.attack_target(q,label,sample['_source_id'],'S3-v2')
        assert target is not None
        if label['kind']=='exact':
            answer='true' if target else 'false'
            text=f'{answer.capitalize()}. The answer to the original yes-or-no question is {answer}.'
        else:text=f'P(true) = {target:.1f}. The proposition is '+('true.' if target else 'false.')
        text+=f" Scenario detail: '{cue}'."
        modified['criteria']={'true':text,'false':text}
        sample['s3_generation']={'version':VERSION,'seed':seed,'contrary_target':target,'identical_opposite_descriptions':True,'original_answer_kind':label['kind']}
        method='opposite_answer_label_collapse'
    else:
        g.generate_s3(sample,q,state,label)
        sample['s3_generation']={'version':VERSION,'seed':g.stable_rng(sample['_source_id'],'S3')[1],'score_method_unchanged':True}
        return
    sample.update(target_path='question.criteria',perturbed_question_text=g.qtext(modified))
    g.mark_candidate(sample,method,'One fresh criteria rewrite under S3-v2; original instructions and state unchanged.')

if __name__=='__main__':
    if BACKUP.exists():
        assert g.sha(g.DEST)==g.sha(BACKUP/g.DEST.name),'Revision already generated'
        shutil.copy2(BACKUP/g.PROMPT.name,g.PROMPT)
    else:
        BACKUP.mkdir()
        for f in [g.DEST,g.PROMPT,P/'ADbeta1.0-validation.json',P/'ADbeta1.0-README.md']:
            if f.exists():shutil.copy2(f,BACKUP/f.name)
    before=json.loads(g.DEST.read_text());source=json.loads(g.SOURCE.read_text());update_prompt();g.SEED=secrets.randbits(64)
    original={r['question_id']:(r,s['state']) for s in source['scenarios'] for rr in s['questions'].values()for r in rr}
    d=copy.deepcopy(before);counts={};n=0
    for sc in d['scenarios']:
        for rr in sc['questions'].values():
            for r in rr:
                baseline,state=original[r['question_id']];assert r['question']==baseline['question'] and sc['state']==state
                pkg=r['adversarial'];sample=g.base_sample('S3',g.qtext(baseline['question']),state);sample['_source_id']=r['question_id']
                generate(sample,baseline['question'],state,baseline['standard_answer']);del sample['_source_id']
                pkg['samples'][5]=sample;g.validate_package(pkg,baseline['question'],state);n+=1
                counts[sample['method']]=counts.get(sample['method'],0)+1
    for a,b in zip(before['scenarios'],d['scenarios']):
        for typ in a['questions']:
            for x,y in zip(a['questions'][typ],b['questions'][typ]):
                assert [s for s in x['adversarial']['samples']if s['id']!='S3']==[s for s in y['adversarial']['samples']if s['id']!='S3']
    revision={'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'random_seed':g.SEED,'prompt_sha256':g.sha(g.PROMPT),'previous_dataset_sha256':g.sha(g.DEST),'source_sha256':g.sha(g.SOURCE),'regenerated_categories':['S3'],'unchanged_other_samples':8932,'generator_sha256':g.sha(Path(__file__))}
    d['generation_spec'].setdefault('category_revisions',[]).append(revision);d['summary']['methods']['S3']=counts
    g.DEST.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    validation={**revision,'dataset_sha256':g.sha(g.DEST),'passed':True,'s3_candidates':n,'choice_forced_displacement':337,'noul_opposite_collapse':314,'score_preserved_shape':161,'review_status':'pending'}
    (P/'ADbeta1.0-S3-v2-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    with (P/'ADbeta1.0-README.md').open('a')as f:f.write('\n## S3-v2 更新\n\n仅 S3 的 812 个候选从 beta1.0 原题重建。Choice 强制置换正确选项描述，Noul 两个合法键采用相同的反向描述，Score 使用原生成方法和严格评分。其他 8,932 个候选保持不变。新测试见 ADbeta1.0-S3-v2-eval/，此前全量测试是旧 S3 结果。各类别的 prompt/数据哈希见 generation_spec.category_revisions。\n')
    print(json.dumps(validation,ensure_ascii=False))
