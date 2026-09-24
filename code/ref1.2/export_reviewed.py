"""Export the workbench's saved human decisions plus the authorized Jev defaults."""
import collections,datetime,hashlib,json,math,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parent
get=lambda route:json.load(urllib.request.urlopen('http://127.0.0.1:8766/api/'+route))
data=get('dataset');review=get('reviews/export')
labels={r['question_id']:r for r in review['accepted_labels']}
human={r['question_id']:r for r in review['reviews']}
assert len(labels)==len(review['accepted_labels'])
questions=[q for c in data for qs in c['questions'].values() for q in qs]
assert len({q['id'] for q in questions})==len(questions)
assert set(labels)=={q['id'] for q in questions},'Missing or unexpected labels'
for q in questions:
 a=labels[q['id']];v=a['value'];assert a['type']==q['type']
 if q['id'] in human:
  fingerprint=hashlib.sha256(json.dumps({'state':q['state'],'question':q['question']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  assert human[q['id']]['fingerprint']==fingerprint,'Review/input mismatch'
 if isinstance(v,dict):
  assert q['type'] in ['noul','score'] and v['metric']==q['type'] and v['bounds']=='inclusive'
  assert 0<=v['lower']<=v['upper']<=(1 if q['type']=='noul' else len(q['question']['criteria'])-1)
 elif q['type']=='noul':assert type(v)is bool
 elif q['type']=='choice':assert v in q['question']['criteria']
 else:assert type(v) in [int,float] and math.isfinite(v) and 0<=v<=len(q['question']['criteria'])-1
pending=[q['id'] for q in questions if q['baseline_label']['status']=='review' and human.get(q['id'],{}).get('status') not in ['confirmed','corrected','interval']]
assert not pending,'Special questions still need review'
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
stamp=now.strftime('%Y%m%d-%H%M%S')
counts={'scenarios':len(data),'questions':len(questions),'human_reviewed':sum(a['source']=='human_review' for a in labels.values()),'jev_default':sum(a['source']=='jev_default' for a in labels.values()),'interval_answers':sum(isinstance(a['value'],dict) for a in labels.values()),'special_pending':len(pending),'question_types':dict(collections.Counter(q['type'] for q in questions))}
out={'dataset':'ref1.2','exported_at':now.isoformat(),'summary':counts,'说明':{'结构':'每个场景保留完整 state，其下按 noul、choice、score 分类；question 保留原始指令及选项或等级。','标准答案':'standard_answer 是当前采用的评测标签。human_review 表示人工审核，jev_default 表示默认采用稳定 Jev 答案，未经独立人工验证。','区间':'kind=interval 时上下限均包含在内。noul 使用 0–1 的 P(true)，score 使用原始评分单位。','固定标签':'kind=exact：noul 为布尔值，choice 为原选项键，score 为连续评分。未在本文件中新增固定标签的评分阈值。'},'scenarios':[]}
for c in data:
 case={'scenario_id':c['id'],'title':c['title'],'state':c['state'],'questions':{}}
 for typ,qs in c['questions'].items():
  case['questions'][typ]=[]
  for q in qs:
   a=labels[q['id']];v=a['value'];answer={'kind':'interval' if isinstance(v,dict) else 'exact','value':v,'source':a['source']}
   if a.get('note'):answer['note']=a['note']
   if q['id'] in human:answer['review_revision']=human[q['id']]['revision']
   case['questions'][typ].append({'question_id':q['id'],'question_type':q['type'],'question':q['question'],'standard_answer':answer})
 out['scenarios'].append(case)
p=root/'exports'/('ref1.2_场景-问题-标准答案_'+stamp+'.json');p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
archive=root/'exports'/('审核记录快照_'+stamp+'.json');archive.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
loaded=json.loads(p.read_text());assert sum(len(qs) for c in loaded['scenarios'] for qs in c['questions'].values())==len(questions)
assert get('reviews/export')['history']==review['history'],'Reviews changed during export; rerun export'
print(json.dumps({'file':str(p),'audit_snapshot':str(archive),'summary':counts,'bytes':p.stat().st_size},ensure_ascii=False))
