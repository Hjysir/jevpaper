import asyncio,json,datetime,hashlib
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';out=P/('S3-choice-sibling-smoke-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
d=json.loads((P/'ADbeta1.0.json').read_text());qid='official-U-dd88fef171ec/gen-choice-01'
for sc in d['scenarios']:
 for r in sc['questions']['choice']:
  if r['question_id']==qid:record=r;state=sc['state']
q=record['question'];modified=json.loads(json.dumps(q));modified['new_criterira']=json.loads(record['adversarial']['samples'][5]['perturbed_question_text'])['criteria'];variants={'clean':q,'sibling_new_criterira':modified}
(out/'inputs.json').write_text(json.dumps({'question_id':qid,'state':state,'variants':variants,'model':b.MODEL,'label':record['standard_answer'],'repeats':3},ensure_ascii=False,indent=2)+'\n')
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(name,q,rep):
   body=b.request_bytes(state,[('test',json.dumps(q,ensure_ascii=False))])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as response:
    status=response.status;raw=await response.text()
   try:data=json.loads(raw)
   except ValueError:data={'text':raw[:1000].replace(key,'[REDACTED]')}
   result={'variant':name,'repeat':rep,'http_status':status,'body_sha256':hashlib.sha256(body).hexdigest(),'response':data}
   if status==200 and data.get('model')==b.MODEL and'test'in data.get('answers',{}):
    answer=data['answers']['test'];result.update(choice=answer['choice'],probabilities=answer['probabilities'],strict_correct=answer['choice']==record['standard_answer']['value'])
   return result
  rows=await asyncio.gather(*(call(name,q,rep)for rep in range(1,4)for name,q in variants.items()))
 (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 summary={name:{'http_statuses':[r['http_status']for r in rows if r['variant']==name],'answers':[r.get('choice')for r in rows if r['variant']==name],'probabilities':[r.get('probabilities')for r in rows if r['variant']==name],'errors':sum(not r['strict_correct']for r in rows if r['variant']==name and'strict_correct'in r)}for name in variants}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(out),'summary':summary,'failures':[r for r in rows if'choice'not in r]},ensure_ascii=False))
asyncio.run(main())
