import json,pathlib,statistics,collections,math,hashlib
P=pathlib.Path(__file__).resolve().parent
RULES={'repeats':5,'noul':{'same_band_all_runs':True,'false_lte':0.4,'true_gte':0.6,'max_probability_range':0.1},'choice':{'same_winner_all_runs':True,'min_winner_probability':0.7,'max_winner_probability_range':0.1},'score':{'same_top_level_all_runs':True,'min_top_level_probability':0.7,'max_score_range':0.25},'notes':'Project-selected conservative screening, not official thresholds. Labels are Jev consensus pseudo-labels, not independently verified gold. Confidence is retained separately and is not used as top-label probability.'}
def reason_applicability(index,q):
 t=q['question']['instructions'];t=t if isinstance(t,str) else ''
 if index in [27,28,29,30] and q['origin']['kind']=='retained_ref1.1':
  if index==29 and 'kickoff call' in t:return '原题前提不适用：此 State 未包含 kickoff call'
  if index in [27,30] and 'If the date' in t and 'absolute calendar date' in t:return '原题前提不适用：日期采用相对表达'
  if index in [28,29] and ('relative to today' in t or 'names a day of the week' in t or 'names a weekday' in t):return '原题前提不适用：已给出绝对日期，未命名星期'
  if index==30 and ('names a day of the week' in t or 'names a weekday' in t):return '原题前提不适用：today 未命名具体星期'
 if index==43 and q['origin']['kind']=='retained_ref1.1':return '原题标准需复核：true 的 structural starch 与 false 排除 cookie/wafer 存在解释重叠'
 return None

def main():
 cases=json.load(open(P/'input.json'));labels=[];errors=[];reqs=[]
 for index,g in enumerate(cases):
  runs=[]
  for r in range(1,6):
   p=P/'responses'/f'{g["id"]}-r{r}.json'
   if p.exists():
    obj=json.load(open(p));reqs.append(obj)
    if obj['status']=='ok':runs.append((r,obj,str(p.relative_to(P))))
    else:errors.append({'state':g['id'],'round':r,'status':obj['status']})
  for typ,qs in g['questions'].items():
   for q in qs:
    q['original_results']=[{'round':r,'model':o['response']['model'],'answer':o['response']['answers'][q['id']],'response_file':fn} for r,o,fn in runs]
    ans=[x['answer'] for x in q['original_results']];reasons=[];v={'count':len(ans)};candidate=None
    if len(ans)!=5:reasons.append('有效响应不足5次')
    if ans:
     if typ=='noul':
      ps=[a['noul'] for a in ans];assert all(isinstance(p,(float,int)) and 0<=p<=1 for p in ps)
      bands=['false' if p<=.4 else 'true' if p>=.6 else 'review' for p in ps]
      v.update(probabilities=ps,mean=statistics.mean(ps),min=min(ps),max=max(ps),bands=bands)
      candidate={'value':statistics.mean(ps)>=.5,'probability_mean':statistics.mean(ps)}
      if len(set(bands))>1:reasons.append('轮次判断区间不一致')
      if 'review' in bands:reasons.append('接近判断边界：至少一轮在(0.4,0.6)')
      if max(ps)-min(ps)>.1000001:reasons.append('是概率波动超过0.10')
     else:
      winners=[];ps=[];scores=[];distributions=[]
      for a in ans:
       dist=a['probabilities'];assert dist and all(0<=p<=1 for p in dist.values());assert abs(sum(dist.values())-1)<.05
       top=max(dist,key=dist.get);winners.append(a['choice'] if typ=='choice' else top);ps.append(dist.get(str(winners[-1]),0));distributions.append(dist)
       if typ=='score':scores.append(a['score']);assert 0<=a['score']<=len(q['question']['criteria'])-1
      counts=collections.Counter(winners);winner=counts.most_common(1)[0][0];keys=set().union(*distributions)
      mean_dist={k:statistics.mean(d.get(k,0) for d in distributions) for k in sorted(keys)}
      v.update(winners=winners,votes=dict(counts),winner_probabilities=ps,mean_probabilities=mean_dist,confidence=[a.get('confidence') for a in ans])
      candidate={'value':winner if typ=='choice' else int(winner),'mean_probabilities':mean_dist}
      if len(counts)>1:reasons.append('5次选择/最高概率等级不一致')
      if min(ps)<.7:reasons.append('至少一轮最高选项概率低于0.70')
      if typ=='choice' and max(ps)-min(ps)>.1000001:reasons.append('获选选项概率波动超过0.10')
      if typ=='score':
       v.update(scores=scores,mean=statistics.mean(scores),min=min(scores),max=max(scores));candidate['score_mean']=statistics.mean(scores)
       if max(scores)-min(scores)>.2500001:reasons.append('评分跨度超过0.25个等级')
    applicability=reason_applicability(index,q)
    if applicability:reasons.append(applicability)
    label={'question_id':q['id'],'state_id':g['id'],'state_title':g['title'],'type':typ,'origin':q['origin'],'status':'review' if reasons else 'stable','label_source':'jev_5run_consensus','gold_verified':False,'label':None if reasons else candidate,'candidate':candidate,'reasons':reasons,'statistics':v,'rules':RULES[typ]}
    q['baseline_label']=label;labels.append(label)
 types=collections.Counter(q['type'] for q in labels);status=collections.Counter(q['status'] for q in labels);reasons=collections.Counter(r for q in labels for r in q['reasons']);usage=collections.Counter()
 for r in reqs:
  if r['status']=='ok':usage.update(r['response'].get('usage',{}))
 summary={'states':len(cases),'questions':len(labels),'by_type':dict(types),'statuses':dict(status),'review_reasons':dict(reasons),'requests':len(reqs),'successful_requests':sum(r['status']=='ok' for r in reqs),'answers':sum(x['statistics']['count'] for x in labels),'usage':dict(usage),'errors':errors,'model':'jev-1.13.0','repeats':5,'independently_verified_gold':False}
 for name,obj in [('dataset.json',cases),('labels.json',labels),('review-queue.json',[q for q in labels if q['status']=='review']),('stable-labels.json',[q for q in labels if q['status']=='stable']),('summary.json',summary),('label-rules.json',RULES)]:
  (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
