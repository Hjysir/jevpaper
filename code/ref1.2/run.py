import json,pathlib,urllib.request,urllib.error,concurrent.futures,time,hashlib,datetime,collections,sys,os
P=pathlib.Path(__file__).resolve().parent
MODEL='jev-1.13.0'
def dump(path,obj):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2));t.replace(path)
def credential():
 for p in [pathlib.Path('/Users/hujianyi/Desktop/具身智能/jev-workbench/.env'),pathlib.Path('/Users/hujianyi/.codex/tools/jev-use/credentials.env')]:
  if p.exists():
   for line in p.read_text().splitlines():
    k,sep,v=line.strip().partition('=')
    if sep and k in ['TYPESAFE_API_KEY','TYPESAFE_API_TOKEN'] and v.strip():return v.strip().strip('\"\'')
 if os.getenv('TYPESAFE_API_KEY'):return os.environ['TYPESAFE_API_KEY']
 raise RuntimeError('No configured credential')
def call(g,repeat,key):
 folder=P/'responses';folder.mkdir(exist_ok=True);dest=folder/(g['id']+f'-r{repeat}.json')
 qs={q['id']:q['question'] for v in g['questions'].values() for q in v}
 payload={'model':MODEL,'state':g['state'],'questions':qs};digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
 if dest.exists():
  old=json.loads(dest.read_text());assert old['payload_sha256']==digest
  if old['status']=='ok':return old
 result={'state_id':g['id'],'repeat':repeat,'payload_sha256':digest,'question_count':len(qs),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'pending'}
 for attempt in range(3):
  start=time.monotonic()
  try:
   req=urllib.request.Request('https://api.typesafe.ai/v1/systemone',json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=180) as r:body=json.load(r);result['request_id']=r.headers.get('x-request-id')
   assert set(body.get('answers',{}))==set(qs),'Response question IDs mismatch'
   assert body.get('model')==MODEL, 'Resolved model differs from requested model'
   result.update(status='ok',response=body,elapsed_seconds=time.monotonic()-start,attempt=attempt+1);dump(dest,result);return result
  except urllib.error.HTTPError as e:
   result.update(status='http_error',http_status=e.code,error=e.read().decode(errors='replace')[:1500].replace(key,'[REDACTED]'))
   retry=e.code in [429,500,502,503,504]
  except Exception as e:
   result.update(status='error',error=type(e).__name__+': '+str(e).replace(key,'[REDACTED]'));retry=True
  result['elapsed_seconds']=time.monotonic()-start;result['attempt']=attempt+1;dump(dest,result)
  if not retry:break
  time.sleep(2**attempt*2)
 return result

def main():
 gs=json.load(open(P/'input.json'));key=credential();batches=[];b=[];n=0
 for g in gs:
  size=sum(map(len,g['questions'].values()))
  if b and n+size>100:batches.append(b);b=[];n=0
  b.append(g);n+=size
 if b:batches.append(b)
 dump(P/'run-config.json',{'model':MODEL,'repeats':5,'concurrency':6,'batch_question_limit':100,'state_unchanged':True,'same_state_questions_batched':True,'batch_state_ids':[[g['id'] for g in b] for b in batches]})
 if '--canary' in sys.argv:
  r=call(gs[0],1,key);print(json.dumps({k:v for k,v in r.items() if k not in ['response','payload_sha256']},ensure_ascii=False),flush=True);return
 for bi,b in enumerate(batches,1):
  print(f'Batch {bi}/{len(batches)}: {sum(sum(map(len,g["questions"].values())) for g in b)} questions x 5',flush=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
   fs=[pool.submit(call,g,r,key) for r in range(1,6) for g in b]
   done=0;errors=[]
   for f in concurrent.futures.as_completed(fs):
    r=f.result();done+=1
    if r['status']!='ok':errors.append({k:v for k,v in r.items() if k not in ['response']})
    print(json.dumps({'completed':done,'total':len(fs),'state':r['state_id'],'round':r['repeat'],'status':r['status'],'elapsed':round(r.get('elapsed_seconds',0),1)}),flush=True)
  dump(P/f'batch-{bi:02}-status.json',{'completed_requests':len(fs),'errors':errors})
  if errors: print('Batch errors recorded; stopping for inspection',flush=True);return
 print('ALL COMPLETE',flush=True)
if __name__=='__main__':main()
