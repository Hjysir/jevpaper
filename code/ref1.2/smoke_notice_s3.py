import asyncio,json,hashlib,datetime
from pathlib import Path
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';out=P/('S3-notice-smoke-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
d=json.loads((P/'ADbeta1.0.json').read_text());qid='official-U-7f6406e52f1f/q000'
for sc in d['scenarios']:
 for r in sc['questions']['noul']:
  if r['question_id']==qid:record=r;state=sc['state']
original=record['question'];direct=json.loads(record['adversarial']['samples'][5]['perturbed_question_text']);wrapped=json.loads(json.dumps(direct));wrapped['criteria']={'notice':direct['criteria']}
assert state=='Help! My payouts have been failing for 3 days.'
variants={'clean':original,'direct':direct,'notice':wrapped}
manifest={'question_id':qid,'model':b.MODEL,'state':state,'label':record['standard_answer'],'variants':variants,'repetitions':3,'scope':'Single-question smoke test; notice is nested under criteria. Same rule text and state. No dataset/prompt modifications.'}
(out/'inputs.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(name,q,repeat):
   body=b.request_bytes(state,[('test',json.dumps(q,ensure_ascii=False))])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as resp:
    status=resp.status;text=await resp.text();rid=resp.headers.get('x-request-id')
   try:data=json.loads(text)
   except ValueError:data={'text':text[:1500].replace(key,'[REDACTED]')}
   result={'variant':name,'repeat':repeat,'http_status':status,'request_id':rid,'body_sha256':hashlib.sha256(body).hexdigest(),'response':data}
   if status==200 and data.get('model')==b.MODEL and 'test'in data.get('answers',{}):
    answer=data['answers']['test'];value,correct,_=b.score({'type':'noul','label':record['standard_answer']},answer);result.update(p_true=value,strict_correct=correct)
   return result
  rows=await asyncio.gather(*(call(name,q,rep)for rep in range(1,4)for name,q in variants.items()))
 (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 summary={}
 for name in variants:
  rr=[r for r in rows if r['variant']==name];ok=[r for r in rr if'p_true'in r];summary[name]={'attempted':len(rr),'answered':len(ok),'http_statuses':[r['http_status']for r in rr],'p_true':[r['p_true']for r in ok],'mean_p_true':sum(r['p_true']for r in ok)/len(ok)if ok else None,'strict_errors':sum(not r['strict_correct']for r in ok)}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'output':str(out),'summary':summary,'errors':[r for r in rows if'p_true'not in r]},ensure_ascii=False))
 lines=['# S3 notice 最小对照','', '同一道 urgency 题，原标签 true。clean、direct、criteria.notice 各 3 次；两种扰动规则文本完全相同。没有修改正式数据集或 prompt。','', '| 输入 | HTTP 状态 | P(true) | 原标签错误数 |','|---|---|---|---|']
 for name,s in summary.items():lines.append(f"| {name} | {s['http_statuses']} | {s['p_true']} | {s['strict_errors']}/{s['answered']} |")
 lines+=['','接口接受仅代表请求可处理，不证明 notice 内的内容被作为 Noul 标签定义使用。样本量只有一道题，不能外推为全体 S3 效果。失败请求不算模型错误。']
 (out/'report.md').write_text('\n'.join(lines)+'\n')
asyncio.run(main())
