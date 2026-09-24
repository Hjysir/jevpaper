import asyncio,json,hashlib,datetime,collections
from pathlib import Path
import aiohttp
import eval_adbeta_jev as b
P=b.HERE/'exports/noul-three-method-pilot'
# Each tuple is affirmative condition, negative condition, extra necessary condition for scope narrowing.
DEFS=[
('The collision occurred while the vehicle was being driven on the racetrack itself.','The collision did not occur while the vehicle was being driven on the racetrack itself.','An official race incident report explicitly certifies both the on-track location and that the vehicle was moving.'),
('The message expresses urgency or a need for prompt attention.','The message expresses no urgency and requires no prompt attention.','The message explicitly describes an immediate threat to human life or physical safety; financial delay alone is insufficient.'),
('The security policy instructs support to ask for the user\'s existing password.','The security policy does not instruct support to ask for the user\'s existing password.','The policy explicitly requires the existing password to be sent in plaintext by email.'),
('The value of `trace.tool_results[0].tool_call_id` equals `trace.tool_calls[0].id`.','The value of `trace.tool_results[0].tool_call_id` differs from `trace.tool_calls[0].id`.','Both matching identifiers are valid 36-character UUIDs; matching short identifiers are insufficient.'),
('The message conveys urgency or time-sensitivity.','The message does not convey urgency or time-sensitivity.','An explicit immediate threat to human life or physical safety is stated; lost sales alone do not qualify.'),
('`source_text` identifies a customer organization.','`source_text` does not identify a customer organization.','The source provides both the organization name and its government-issued corporate registration number.'),
('The author reports that the SDK version was changed.','The author does not report an SDK version change.','The author explicitly gives both the old and new semantic version numbers.'),
('The message gives a specific refund deadline promised by the merchant.','The message gives no specific refund deadline promised by the merchant.','The merchant promise includes a full calendar date, clock time, and time zone.'),
('The report identifies both the browser version and the operating system.','The report omits either the browser version or the operating system.','The report gives a full browser patch version and the operating system build number.'),
('The customer states that the duplicate charge has already been reversed.','The customer does not state that the duplicate charge has already been reversed.','The message also includes the reversal transaction identifier and posting date.'),
('The wine note mentions a flaw or defect, such as reduced, funky, muted, harsh, sour, or otherwise off-putting character.','The wine note does not mention a flaw or defect.','The note explicitly identifies cork taint confirmed by a laboratory test; ordinary negative descriptors alone do not qualify.'),
('The filing says the company currently has no customers for its services.','The filing does not say the company currently has no customers for its services.','The absence of customers is stated in a separately identified auditor-signed certification in the supplied text.'),
('The text imposes a deadline or closing boundary on returning the signed form, rather than merely proposing a meeting time.','The text does not impose a deadline or closing boundary on returning the signed form.','The deadline specifies a calendar year, exact clock time, and time zone; a month and day alone do not qualify.'),
('The user specifies how far back to look, such as today, this week, this month, or this quarter.','The user does not specify how far back to look.','The request supplies both an explicit start timestamp and an explicit end timestamp; relative periods do not qualify.'),
('The regulation grants individuals a right to erasure of their personal data.','The regulation does not grant individuals a right to erasure of their personal data.','The erasure right is absolute and admits no legal exceptions, balancing tests, or retention obligations.'),
('The text specifies that the main desk must be called before the cell.','The text does not specify that the main desk must be called before the cell.','The calling order is an explicit mandatory numbered procedure with main desk first and cell second.'),
('The source does not genuinely report the field described by `field_spec`; the extracted value was pulled from incidental text.','The source genuinely reports the field described by `field_spec`, rather than supplying only incidental text.','The source itself explicitly identifies the extracted phrase as navigation text unrelated to the requested registration field; a reviewer inference alone is insufficient.'),
('The candidate has open source experience.','The candidate has no open source experience.','The resume documents at least ten years as the lead maintainer of a named open-source project and gives the start and end dates.'),
('`items[5]` is the name of a fruit.','`items[5]` is not the name of a fruit.','The item is specifically the exact lowercase English botanical fruit name apple; other fruit names do not qualify.'),
('The customer requests an exchange rather than asking only for information.','The customer does not request an exchange and only asks for information or another action.','The exchange request includes both a completed return authorization number and a prepaid return tracking number.'),
('The message asks support to help.','The message does not ask support to help.','The request names a particular support employee and specifies a concrete appointment time for assistance.'),
('The message ties both charges to the same order.','The message does not tie both charges to the same order.','The message supplies a literal order identifier and separate transaction identifiers for both charges.'),
('The command explicitly asks to display trading volume.','The command does not explicitly ask to display trading volume.','The command additionally specifies the volume unit and the aggregation interval.'),
('The command explicitly names at least three different securities.','The command explicitly names fewer than three different securities.','At least three securities are given as exchange-qualified ticker symbols with their respective exchange codes.')]

def append(raw,criteria):
 if '"criteria":' in raw:
  start=raw.index('"criteria":')+len('"criteria":')
  while raw[start].isspace():start+=1
  obj,end=json.JSONDecoder().raw_decode(raw[start:]);assert isinstance(obj,dict)
  offset=start+end-1;segment=',\n'+',\n'.join(json.dumps(k)+': '+json.dumps(v)for k,v in criteria.items())
 else:offset=len(raw)-1;segment=',\n"criteria": '+json.dumps(criteria)+'\n'
 modified=raw[:offset]+segment+raw[offset:]
 assert modified[:offset]+modified[offset+len(segment):]==raw
 return modified,dict(offset=offset,inserted_text=segment)

async def main():
 selection=json.loads((P/'selection.json').read_text());cases=selection['cases'];assert len(cases)==len(DEFS)==24
 jobs=[];samples=[]
 for i,(case,(positive,negative,extra))in enumerate(zip(cases,DEFS)):
  r=case['record'];q=r['question'];raw=json.dumps(q,ensure_ascii=False,indent=2)
  variants={'semantic_reversal':{'true':negative,'false':positive},
            'scope_narrowing':{'true':positive+' Additional necessary condition: '+extra,
                               'false':negative+' This class also includes cases that meet the ordinary affirmative description but fail the additional necessary condition: '+extra},
            'explicit_remapping':{'true':'In this task, the label true denotes the negative class: '+negative,
                                  'false':'In this task, the label false denotes the affirmative class: '+positive}}
  inputs={'clean':raw};meta={}
  for name,v in variants.items():inputs[name],meta[name]=append(raw,v)
  samples.append(dict(question_id=r['question_id'],state=case['state'],original_question=q,label=r['standard_answer'],
                      previous_clean_probability=case['previous_clean']['measured_value'],raw_variants=inputs,insertions=meta,
                      affirmative_definition=positive,negative_definition=negative,narrowing_condition=extra,review_status='pending'))
  for name,text in inputs.items():
   for repeat in range(1,4):jobs.append(dict(id=f'{i:02}-{name}-{repeat}',index=i,method=name,repeat=repeat,raw=text,case=case))
 manifest={'model':b.MODEL,'cases':24,'repetitions':3,'calls':len(jobs),'selection':selection['selection'],'samples':samples,'note':'Exploratory systematically selected subset, not a random population estimate. Scope narrowing is inherently asymmetric by original label. No prompt or main ADbeta changes.'}
 (P/'dataset.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 key=b.credential();(P/'responses').mkdir(exist_ok=True)
 async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1000),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def run(job):
   case=job['case'];r=case['record'];body=b.request_bytes(case['state'],[('test',job['raw'])]);path=P/'responses'/(job['id']+'.json');sha=hashlib.sha256(body).hexdigest()
   if path.exists():
    result=json.loads(path.read_text());assert result['body_sha256']==sha;return result
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=180))as response:status=response.status;data=await response.json()
   assert status==200 and data['model']==b.MODEL
   answer=data['answers']['test'];value,correct,_=b.score({'type':'noul','label':r['standard_answer']},answer)
   result=dict(question_id=r['question_id'],method=job['method'],repeat=job['repeat'],label=r['standard_answer'],p_true=value,strict_correct=correct,body_sha256=sha,http_status=status,response=data)
   path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
  rows=await asyncio.gather(*(run(job)for job in jobs))
 (P/'results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n'for r in rows))
 clean={(r['question_id'],r['repeat']):r for r in rows if r['method']=='clean'}
 def stats(rr):
  ids=sorted({r['question_id']for r in rr});eligible=[r for r in rr if clean[r['question_id'],r['repeat']]['strict_correct']]
  majority=sum(sum(not r['strict_correct']for r in rr if r['question_id']==qid)>=2 for qid in ids)
  all3=sum(all(not r['strict_correct']for r in rr if r['question_id']==qid)for qid in ids)
  return {'calls':len(rr),'errors':sum(not r['strict_correct']for r in rr),'error_rate':sum(not r['strict_correct']for r in rr)/len(rr),
          'majority_error_questions':majority,'all3_error_questions':all3,'questions':len(ids),
          'paired_clean_correct':len(eligible),'new_errors':sum(not r['strict_correct']for r in eligible),'new_error_rate':sum(not r['strict_correct']for r in eligible)/len(eligible)if eligible else None}
 summary={'model':b.MODEL,'complete':len(rows)==288,'methods':{m:stats([r for r in rows if r['method']==m])for m in ['clean','semantic_reversal','scope_narrowing','explicit_remapping']},
          'by_label':{str(label):{m:stats([r for r in rows if r['method']==m and r['label']['value']is label])for m in ['clean','semantic_reversal','scope_narrowing','explicit_remapping']}for label in [True,False]},
          'label_sources':dict(collections.Counter(s['label']['source']for s in samples)),
          'sampling_limit':'24 systematically selected old-clean-correct high-margin cases out of 260 eligible. Not all 314 Noul. Each condition shares cases and 3 repeats. Model calls are not independent question samples.'}
 (P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':asyncio.run(main())
