import asyncio,json,datetime,hashlib
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';out=P/('S3-choice-attack-marker-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
d=json.loads((P/'ADbeta1.0.json').read_text());qid='official-U-dd88fef171ec/gen-choice-01'
for sc in d['scenarios']:
 for r in sc['questions']['choice']:
  if r['question_id']==qid:record=r;state=sc['state']
q=record['question'];sample=record['adversarial']['samples'][5];original=record['adversarial']['original_question_text'];direct=sample['perturbed_question_text'];offset=sample['s3_generation']['insertion_offset'];swapped=json.loads(direct)['criteria']
segment=',\n'+',\n'.join('    '+json.dumps(k)+': '+json.dumps(v+' (attack)',ensure_ascii=False)for k,v in swapped.items());marked=original[:offset]+segment+original[offset:]
assert marked[:offset]+marked[offset+len(segment):]==original
variants={'clean':original,'direct_unmarked':direct,'direct_attack_marker':marked}
(out/'inputs.json').write_text(json.dumps({'question_id':qid,'state':state,'raw_questions':variants,'model':b.MODEL,'label':record['standard_answer'],'repeats':3,'marker':' (attack)','placement':'Only appended descriptions; original criteria untouched; duplicate keys preserved in HTTP bytes.'},ensure_ascii=False,indent=2)+'\n')
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(name,raw,rep):
   body=b.request_bytes(state,[('test',raw)])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as response:
    status=response.status;text=await response.text()
   try:data=json.loads(text)
   except ValueError:data={'text':text[:1000].replace(key,'[REDACTED]')}
   result={'variant':name,'repeat':rep,'http_status':status,'body_sha256':hashlib.sha256(body).hexdigest(),'response':data}
   if status==200 and data.get('model')==b.MODEL and'test'in data.get('answers',{}):
    a=data['answers']['test'];result.update(choice=a['choice'],probabilities=a['probabilities'],strict_correct=a['choice']==record['standard_answer']['value'])
   return result
  rows=await asyncio.gather(*(call(name,raw,rep)for rep in range(1,4)for name,raw in variants.items()))
 (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 summary={}
 for name in variants:
  rr=[r for r in rows if r['variant']==name];ok=[r for r in rr if'choice'in r];summary[name]={'http_statuses':[r['http_status']for r in rr],'answers':[r['choice']for r in ok],'probabilities':[r['probabilities']for r in ok],'errors':sum(not r['strict_correct']for r in ok),'answered':len(ok)}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(out),'summary':summary},ensure_ascii=False))
asyncio.run(main())
