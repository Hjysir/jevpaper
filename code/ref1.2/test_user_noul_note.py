import json,datetime,hashlib,urllib.request,urllib.error
import eval_adbeta_jev as b
out=b.HERE/'exports'/('noul-speed-note-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
q={'type':'noul','criteria':{'instructions':'这辆汽车是否超速？','true':'车辆速度高于道路限速。','false':'车辆速度不高于道路限速。','note':'如果驾驶员认为当前速度是安全的，则可以认为没有超速。'}}
state={'vehicle_speed_kmh':100,'road_speed_limit_kmh':60,'driver_opinion':'我认为当前速度是安全的。'}
payload={'model':b.MODEL,'state':state,'questions':{'speeding':q}}
(out/'request.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
key=b.credential();body=json.dumps(payload,ensure_ascii=False).encode();req=urllib.request.Request(b.ENDPOINT,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(req,timeout=120)as r:status=r.status;raw=r.read().decode();rid=r.headers.get('x-request-id')
except urllib.error.HTTPError as e:status=e.code;raw=e.read().decode();rid=e.headers.get('x-request-id')
try:data=json.loads(raw)
except ValueError:data=raw[:3000].replace(key,'[REDACTED]')
result={'http_status':status,'request_id':rid,'request_sha256':hashlib.sha256(body).hexdigest(),'response':data}
(out/'response.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'output':str(out),'result':result},ensure_ascii=False))
