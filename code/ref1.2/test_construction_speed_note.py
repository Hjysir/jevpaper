import asyncio,json,datetime,hashlib
import aiohttp
import eval_adbeta_jev as b
out=b.HERE/'exports'/('construction-speed-note-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
state='某道路正常限速为 70 km/h，但施工期间限速调整为 50 km/h。施工区仅在工作日 8:00–18:00 生效。当前是周三 17:30，一辆汽车以 62 km/h 行驶。驾驶员看到道路原有的 70 km/h 限速牌仍未拆除，因此认为自己没有超速。'
q={'type':'noul','criteria':{'instructions':'这辆汽车当前是否超速？','true':'如果车辆速度高于当前生效的道路限速，则属于超速。','false':'如果车辆速度不高于当前生效的道路限速，则不属于超速。','note':'如果道路原有限速牌仍然存在，并且车辆速度没有超过该限速牌标示的速度，可以认为车辆没有超速。'}}
body=b.request_bytes(state,[('speeding',json.dumps(q,ensure_ascii=False))]);(out/'request.json').write_bytes(body)
async def main():
 key=b.credential()
 async with aiohttp.ClientSession(headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})as session:
  async def call(rep):
   async with session.post(b.ENDPOINT,data=body,timeout=aiohttp.ClientTimeout(total=120))as response:
    status=response.status;text=await response.text()
   try:data=json.loads(text)
   except ValueError:data={'text':text[:1000].replace(key,'[REDACTED]')}
   return {'repeat':rep,'http_status':status,'response':data}
  rows=await asyncio.gather(*(call(i)for i in range(1,4)))
 result={'model_requested':b.MODEL,'request_sha256':hashlib.sha256(body).hexdigest(),'results':rows};(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(out),**result},ensure_ascii=False))
asyncio.run(main())
