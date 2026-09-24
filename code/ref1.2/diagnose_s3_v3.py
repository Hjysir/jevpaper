import asyncio,json,hashlib,collections
from pathlib import Path
import aiohttp
import eval_adbeta_jev as base
P=base.HERE/'exports';E=P/'ADbeta1.0-S3-v3-eval'
async def main():
 d=json.loads((P/'ADbeta1.0.json').read_text());rs=[json.loads(x)for x in(E/'results.jsonl').read_text().splitlines()];ix={r['question_id']:r for r in rs};records=[]
 for sc in d['scenarios']:
  for rr in sc['questions'].values():
   for r in rr:records.append((r,sc['state'],r['adversarial']['samples'][5]))
 groups={}
 for method in sorted({s['method']for r,state,s in records}):
  rows=[ix[r['question_id']]for r,state,s in records if s['method']==method];errors=sum(not r['strict_correct']for r in rows);groups[method]={'count':len(rows),'errors':errors,'error_rate':errors/len(rows)}
 selected=[]
 for typ in ['noul','choice','score']:
  available=[t for t in records if t[0]['question_type']==typ and t[2]['s3_generation']['duplicate_key_expected']]
  available.sort(key=lambda t:(not any(x in str(t[0]['question']).lower()for x in ['sandwich','convey urgency']),t[0]['question_id']))
  selected+=available[:4]
 key=base.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(t):
   r,state,s=t;previous=ix[r['question_id']];iid=previous['item_id'];raw=s['perturbed_question_text'];canonical=json.dumps(json.loads(raw),ensure_ascii=False)
   body=base.request_bytes(state,[(iid,canonical)])
   async with session.post(base.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as response:
    status=response.status;data=await response.json()
   assert status==200 and data['model']==base.MODEL
   answer=data['answers'][iid];item={'type':r['question_type'],'label':r['standard_answer']};value,correct,_=base.score(item,answer)
   return {'question_id':r['question_id'],'type':r['question_type'],'http_status':status,'canonical_body_sha256':hashlib.sha256(body).hexdigest(),'raw_duplicate_value':previous['measured_value'],'last_wins_value':value,'same_value':previous['measured_value']==value,'raw_correct':previous['strict_correct'],'last_wins_correct':correct,'response':data,'question':r['question']}
  results=await asyncio.gather(*(call(t)for t in selected))
 diag={'diagnostic_only_not_in_main_error_rate':True,'matched_values':sum(r['same_value']for r in results),'count':len(results),'results':results,'conclusion':'Agreement is consistent with last-wins parsing, but does not prove server internals or model-visible representation. Stochastic differences cannot prove duplicate visibility either.'}
 (E/'parser-diagnostic.json').write_text(json.dumps(diag,ensure_ascii=False,indent=2)+'\n')
 summary=json.loads((E/'summary.json').read_text());summary['by_generation_method']=groups;summary['parser_diagnostic']={k:v for k,v in diag.items()if k!='results'};(E/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with(E/'report.md').open('a')as f:
  f.write('\n## Noul 与解析对照\n\n')
  for method,g in groups.items():f.write(f"- {method}: {g['errors']}/{g['count']}，{g['error_rate']:.2%}。\n")
  f.write(f"\n另行测试 {len(results)} 条去掉前一组重复键、仅保留后一组的等价输入，{diag['matched_values']} 条原始数值完全相同。此对照不计入主错误率。结果不能证明服务端是否将两组规则同时送入模型。\n")
  for r in results:
   if r['type']=='noul':f.write(f"\n{r['question_id']}: {r['question']['instructions']}；重复键输出 {r['raw_duplicate_value']}，仅保留后一组输出 {r['last_wins_value']}。\n")
 print(json.dumps({'groups':groups,'diagnostic':diag},ensure_ascii=False))
if __name__=='__main__':asyncio.run(main())
