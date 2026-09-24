import asyncio,json,hashlib,datetime
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports';out=P/('S3-choice-wrapper-smoke-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
d=json.loads((P/'ADbeta1.0.json').read_text());qid='official-U-dd88fef171ec/gen-choice-01'
for sc in d['scenarios']:
 for r in sc['questions']['choice']:
  if r['question_id']==qid:record=r;state=sc['state']
q=record['question'];raw=json.dumps(q,ensure_ascii=False,indent=2);direct=record['adversarial']['samples'][5]['perturbed_question_text'];permuted=json.loads(direct)['criteria']
variants={'clean':raw,'direct_duplicate':direct}
# Preserve every original option and append one wrapper member inside criteria.
for wrapper in ['notice','new_criteria']:
 start=raw.index('"criteria":')+len('"criteria":')
 while raw[start].isspace():start+=1
 obj,end=json.JSONDecoder().raw_decode(raw[start:]);offset=start+end-1
 segment=',\n    '+json.dumps(wrapper)+': '+json.dumps(permuted,ensure_ascii=False,indent=2)+'\n'
 variants[wrapper]=raw[:offset]+segment+raw[offset:]
 assert variants[wrapper][:offset]+variants[wrapper][offset+len(segment):]==raw
manifest={'question_id':qid,'state':state,'original_label':record['standard_answer'],'model':b.MODEL,'repeats':3,'raw_questions':variants,'permuted_options':permuted,'scope':'Append only: wrapper is inside original criteria, preserving original options. Choice map keys may be treated as candidate answers, so record returned distributions and unexpected options.'}
(out/'inputs.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def run(name,text,rep):
   body=b.request_bytes(state,[('test',text)])
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as response:
    status=response.status;raw_response=await response.text()
   try:data=json.loads(raw_response)
   except ValueError:data={'text':raw_response[:1000].replace(key,'[REDACTED]')}
   result={'variant':name,'repeat':rep,'http_status':status,'body_sha256':hashlib.sha256(body).hexdigest(),'response':data}
   if status==200 and data.get('model')==b.MODEL and'test'in data.get('answers',{}):
    answer=data['answers']['test'];value,correct,_=b.score({'type':'choice','label':record['standard_answer']},answer)
    result.update(choice=value,strict_correct=correct,probabilities=answer.get('probabilities'),unexpected_option=value not in q['criteria'])
   return result
  rows=await asyncio.gather(*(run(name,text,rep)for rep in range(1,4)for name,text in variants.items()))
 summary={}
 for name in variants:
  rr=[r for r in rows if r['variant']==name];ok=[r for r in rr if'choice'in r]
  summary[name]={'http_statuses':[r['http_status']for r in rr],'answers':[r['choice']for r in ok],'strict_errors':sum(not r['strict_correct']for r in ok),'answered':len(ok),'probabilities':[r['probabilities']for r in ok],'unexpected_option_count':sum(r['unexpected_option']for r in ok)}
 (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 lines=['# Choice notice/new_criteria 最小对照','', '冰淇淋夹心题，原标签 icecream。每组重复 3 次，规则文本相同。包装位于原 criteria 内，原选项全部保留。正式 prompt 和数据库未改动。','', '| 组别 | HTTP | 选择结果 | 原标签错误数 |','|---|---|---|---|']
 for name,s in summary.items():lines.append(f"| {name} | {s['http_statuses']} | {s['answers']} | {s['strict_errors']}/{s['answered']} |")
 lines+=['','注意：Choice 的 criteria 顶层成员名可能成为输出选项。notice/new_criteria 包装不一定是中性元数据；应检查返回 probabilities 是否新增同名候选。该实验仅覆盖这道题和该嵌套位置。']
 (out/'report.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'output':str(out),'summary':summary,'errors':[r for r in rows if'choice'not in r]},ensure_ascii=False))
asyncio.run(main())
