"""Offline handoff verification; no network, model calls, or source modifications."""
from pathlib import Path
import collections, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
def read(p): return json.loads((ROOT/p).read_text())
def canonical(d):return hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

base=read('data/beta1.0.json')
d=read('data/ADbeta-metadata.json');d['scenarios']=[]
for ref in read('data/scenario-index.json'):
    scenario=read(ref['path']);files=scenario.pop('question_files')
    scenario['questions']={k:[read(p) for p in paths] for k,paths in files.items()}
    d['scenarios'].append(scenario)
def index(obj):return {q['question_id']:(s,q) for s in obj['scenarios'] for qs in s['questions'].values() for q in qs}
b,a=index(base),index(d)
assert len(d['scenarios'])==66 and len(a)==812 and a.keys()==b.keys()
assert canonical(d)==read('provenance/source-snapshot.json')['current_adbeta_canonical_sha256']
counts=collections.Counter();reviews=collections.Counter();sources=collections.Counter();restored=0
for qid,(s,q) in a.items():
    bs,bq=b[qid]
    assert s['state']==bs['state'] and q['question']==bq['question'] and q['standard_answer']==bq['standard_answer']
    samples=q['adversarial']['samples'];assert len(samples)==12 and len({x['id'] for x in samples})==12
    for x in samples:counts[x['id']]+=1;reviews[x['review_status']]+=1
    sources[q['standard_answer']['source']]+=1
    x=next(x for x in samples if x['id']=='S3');g=x['s3_generation'];text=x['perturbed_question_text'];at=g['insertion_offset'];ins=g['inserted_text']
    assert text[at:at+len(ins)]==ins
    original=text[:at]+text[at+len(ins):]
    assert hashlib.sha256(original.encode()).hexdigest()==g['baseline_sha256']
    assert json.loads(original)==q['question'] and x['perturbed_state']==s['state'];restored+=1
assert all(v==812 for v in counts.values())
def rows(run):
    p=ROOT/'experiments'/run
    if (p/'results.jsonl').exists():files=[p/'results.jsonl']
    else:files=[p/r['path'] for r in json.loads((p/'results-index.json').read_text())]
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]
full=rows('ADbeta1.0-jev-eval-1000');s3=rows('ADbeta1.0-S3-v5-eval')
assert len(full)==len({(r['question_id'],r['category']) for r in full})==10556
assert len(s3)==len({r['question_id'] for r in s3})==812
stat={}
for cat in ['clean','Q1','Q2','Q3','S1','S2','S3','T1','T2','T3','P1','P2','P3']:
    rs=[r for r in full if r['category']==cat];assert len(rs)==812
    stat[cat]={'n':len(rs),'strict_errors':sum(not r['strict_correct'] for r in rs)}
assert stat['clean']['strict_errors']==79
assert sum(not r['strict_correct'] for r in s3)==548
assert sum(r['clean_correct'] and not r['strict_correct'] for r in s3)==474
result=dict(passed=True,scenarios=66,questions=812,samples=sum(counts.values()),categories=dict(counts),label_sources=dict(sources),semantic_review=dict(reviews),s3_reversible=restored,full_run=stat,s3_v5={'n':812,'deviations':548,'clean_correct':733,'new_deviations':474},current_adbeta_canonical_sha256=canonical(d))
print(json.dumps(result,ensure_ascii=False,indent=2))
