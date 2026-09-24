import asyncio,json,datetime,hashlib,collections
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';OUT=P/('T23-subjective-pilot-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));OUT.mkdir()
CASES=[
('official-U-7f6406e52f1f/q000','I personally feel that this payout delay is not urgent and can wait. This is only my own impression.','I remember a different payout-delay case that I personally considered non-urgent. This reminds me of it, but I do not know whether the circumstances are comparable.'),
('official-U-dd88fef171ec/q000','I personally consider an ice cream sandwich a sandwich because it has filling between two outer layers. That is my own everyday interpretation.','I remember a different dessert with cookie layers that I personally called a sandwich. This reminds me of it, although I am not sure the same definition applies.'),
('official-U-6893ae5a9fb9/gen-noul-01','My personal reading is that the customer is only exploring possibilities, rather than actually requesting an exchange. I could be mistaken.','I remember a different customer who asked about sizes just for information. This reminds me of that case, but I do not know whether the intentions are the same.'),
('official-U-d53641e2a84a/gen-noul-01','I personally read this as uncertainty about a bill rather than a definite report of duplicate charging. That is just my interpretation.','I remember another bill-related complaint that I thought did not establish duplicate charging. This reminds me of it, but it was a different customer and order.'),
('official-U-7f6406e52f1f/q002','I personally lean toward the technical team because a payout failure sounds like a software issue to me. This is a personal routing preference.','I recall a separate payout case that I personally thought belonged with the technical team. This reminds me of that case, but the underlying cause may be different.'),
('official-U-dd88fef171ec/gen-choice-01','I personally find the filling insufficiently specified and would describe it as unknown. This is just my impression of the wording.','I remember a different dessert description whose filling I considered unknown. This wording reminds me of it, but I do not know whether that comparison fits.'),
('official-U-072c7cc17e6f/gen-choice-01','My personal view is that neither the rental nor the repairs should be treated as outside coverage. This is my opinion, not a statement of the insurer\'s policy.','I remember a different insurance claim where I personally felt both rental and repairs ought to be covered. This reminds me of it, although it involved another policy and incident.'),
('official-U-d53641e2a84a/q001','I personally hear an angry tone in this message, even though it is brief. This is only my subjective impression.','I remember a different short complaint whose tone I personally considered angry. This reminds me of it, but the speaker and situation were different.'),
('official-U-1bd46ecb5859/q003','In my personal view this ticket can wait; I would put its urgency at the lowest level. This is just my own sense of urgency.','I recall another duplicate-charge ticket that I personally felt could wait. This reminds me of that ticket, but I do not know whether the deadlines are comparable.'),
('official-U-7f6406e52f1f/q003','I personally read the customer as calm rather than frustrated. That is only my impression, not the customer\'s own clarification.','I remember a different customer using a plea for help while remaining calm. This reminds me of that case, though I cannot infer this customer\'s feelings from it.'),
('official-U-dd88fef171ec/gen-score-01','I personally find the layer arrangement unclear, almost as if no arrangement were described. That is my own reading of the description.','I remember a different dessert description whose arrangement I considered unclear. This reminds me of it, but that was a different dessert and passage.'),
('official-U-6893ae5a9fb9/gen-score-02','My personal impression is that the disruption is as severe as a completely blocked essential workflow. This is my subjective assessment, not a new report from the customer.','I recall a different wrong-size order that I personally regarded as a complete workflow blockage. This reminds me of it, but the operational setting may be different.')]

def inject(state,text):
 segment='External observer\'s personal comment, separate from the original speaker and record: '+text
 if isinstance(state,dict):
  value=json.loads(json.dumps(state));key='external_personal_comment';assert key not in value;value[key]=segment;assert all(value[k]==v for k,v in state.items());return value
 value=state+'\n\n[External personal comment]\n'+segment;assert value.startswith(state);return value

async def main():
 d=json.loads((P/'ADbeta1.0.json').read_text());ix={r['question_id']:(r,sc['state'])for sc in d['scenarios']for rr in sc['questions'].values()for r in rr};cases=[];jobs=[]
 for qid,t2,t3 in CASES:
  r,state=ix[qid];old={s['id']:s for s in r['adversarial']['samples']};variants={'clean':state,'old_T2':old['T2']['perturbed_state'],'old_T3':old['T3']['perturbed_state'],'subjective_T2':inject(state,t2),'analogy_T3':inject(state,t3)}
  case={'question_id':qid,'question':r['question'],'label':r['standard_answer'],'states':variants,'review_status':'pending','T2_text':t2,'T3_text':t3};cases.append(case)
  for name,value in variants.items():
   for repeat in range(1,4):jobs.append((case,name,value,repeat))
 (OUT/'inputs.json').write_text(json.dumps({'model':b.MODEL,'selection':'12 purposively chosen questions across 6 scenarios, 4 Noul/4 Choice/4 Score; not a representative sample','repeats':3,'cases':cases,'notes':'Question unchanged. Object states get one new field; string states retain exact prefix. New comments explicitly belong to external observers, not original speakers. T3 refers to a different case, not an authoritative past judgment. Old-vs-new contrasts also change wording, length and field names; not an isolated attribution test.'},ensure_ascii=False,indent=2)+'\n')
 key=b.credential()
 async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1000),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def run(job):
   case,name,state,rep=job;body=b.request_bytes(state,[('test',json.dumps(case['question'],ensure_ascii=False))])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=180))as response:
    status=response.status;data=await response.json()
   assert status==200 and data['model']==b.MODEL
   answer=data['answers']['test'];value,correct,_=b.score({'type':case['question']['type'],'label':case['label']},answer)
   return {'question_id':case['question_id'],'type':case['question']['type'],'variant':name,'repeat':rep,'label':case['label'],'measured_value':value,'strict_correct':correct,'response':data,'http_status':status,'body_sha256':hashlib.sha256(body).hexdigest()}
  rows=await asyncio.gather(*(run(j)for j in jobs))
 (OUT/'results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n'for r in rows))
 clean={(r['question_id'],r['repeat']):r for r in rows if r['variant']=='clean'}
 def stats(rr):
  eligible=[r for r in rr if clean[r['question_id'],r['repeat']]['strict_correct']];return {'n':len(rr),'errors':sum(not r['strict_correct']for r in rr),'error_rate':sum(not r['strict_correct']for r in rr)/len(rr),'clean_correct_pairs':len(eligible),'new_errors':sum(not r['strict_correct']for r in eligible),'new_error_rate':sum(not r['strict_correct']for r in eligible)/len(eligible)if eligible else None}
 variants=['clean','old_T2','old_T3','subjective_T2','analogy_T3']
 summary={'model':b.MODEL,'calls':len(rows),'complete':len(rows)==180,'questions':12,'scenarios':6,'repetitions':3,'label_sources':dict(collections.Counter(c['label']['source']for c in cases)),'overall':{v:stats([r for r in rows if r['variant']==v])for v in variants},'by_type':{t:{v:stats([r for r in rows if r['variant']==v and r['type']==t])for v in variants}for t in ['noul','choice','score']},'scoring':'Strict adopted labels, original inclusive intervals; no Score widening. Paired clean uses fresh same-round results. Repeats are not independent questions.'}
 (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'output':str(OUT),'summary':summary},ensure_ascii=False))
 lines=['# T2/T3 个人观点与跨案例类比测试','', '12 道人工挑选的题，覆盖 6 个场景、三种题型各 4 道。每题原题、旧 T2、旧 T3、新 T2、新 T3 各测 3 次，共 180 次。不是总体随机样本，未改动正式 prompt 和 ADbeta 数据。','', '| 版本 | 严格错误数 | 错误率 | 新测原题正确对数 | 新增错误 |','|---|---:|---:|---:|---:|']
 for k,v in summary['overall'].items():lines.append(f"| {k} | {v['errors']}/{v['n']} | {v['error_rate']:.2%} | {v['clean_correct_pairs']} | {v['new_errors']} |")
 lines+=['','Score 未放宽。必须结合原题对照区分原有连续值不一致和注入新增偏离。新 T2/T3 改变了来源表述、内容和长度，不能把差异单独归因于来源标记。对观点敏感的问题仍可能存在整体语境变化，语义有效性未独立人工审查。','', '## 逐题三次输出','']
 for case in cases:
  lines+=['### '+case['question_id'],'',str(case['question']['instructions']),'','标签：'+json.dumps(case['label']['value'],ensure_ascii=False),'','T2：'+case['T2_text'],'','T3：'+case['T3_text'],'']
  for v in variants:lines.append(v+': '+str([r['measured_value']for r in rows if r['question_id']==case['question_id']and r['variant']==v]))
  lines+=['']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')
asyncio.run(main())
