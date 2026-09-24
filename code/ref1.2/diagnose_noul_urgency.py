import asyncio,json,hashlib,datetime
from pathlib import Path
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';OUT=P/'ADbeta1.0-S3-v3-eval/noul-urgency-diagnostic';OUT.mkdir(exist_ok=True)
d=json.loads((P/'ADbeta1.0.json').read_text());qid='official-U-7f6406e52f1f/q001'
for sc in d['scenarios']:
 for rr in sc['questions'].values():
  for r in rr:
   if r['question_id']==qid:record=r;state=sc['state']
q=record['question'];s=record['adversarial']['samples'][5];reversed_q=json.loads(s['perturbed_question_text']);none={k:v for k,v in q.items()if k!='criteria'}
explicit=json.loads(json.dumps(reversed_q));explicit['instructions']='Does the message satisfy the condition described under the true criterion? Use the true and false criteria as the label definitions.'
variants={'original':b.compact(q),'without_criteria':b.compact(none),'reversed_only':b.compact(reversed_q),'appended_duplicate':s['perturbed_question_text'],'explicit_criterion_question':b.compact(explicit)}
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(name,raw,repeat):
   body=b.request_bytes(state,[('test',raw)])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as resp:
    status=resp.status;data=await resp.json()
   assert status==200 and data['model']==b.MODEL
   return {'variant':name,'repeat':repeat,'response':data,'p_true':data['answers']['test']['noul'],'request_sha256':hashlib.sha256(body).hexdigest()}
  rows=await asyncio.gather(*(call(name,raw,rep)for name,raw in variants.items()for rep in range(1,4)))
 result={'question_id':qid,'state':state,'label':record['standard_answer'],'model':b.MODEL,'variants':variants,'repeats':3,'results':rows,'note':'Diagnostic only. Explicit criterion question changes the task and is not part of the benchmark.'}
 (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'state':state,'original':q,'reversed':reversed_q,'results':{name:[r['p_true']for r in rows if r['variant']==name]for name in variants}},ensure_ascii=False))
asyncio.run(main())
