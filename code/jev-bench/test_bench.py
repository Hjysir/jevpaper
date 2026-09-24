import importlib.util,json,tempfile,pathlib,time,unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
spec=importlib.util.spec_from_file_location('bench',pathlib.Path(__file__).with_name('app.py'));bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
class FakeResponse:
 status_code=200
 def __init__(self,payload):self.payload=payload
 def json(self):return {'model':'jev-1.13.0','answers':{'target':{'type':self.payload['questions']['target']['type'],'noul':.9}},'usage':{'input_tokens':1,'output_tokens':1}}
class FakeClient:
 def __init__(self,**kw):pass
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 async def post(self,url,headers,json):return FakeResponse(json)
class Tests(unittest.TestCase):
 def test_workflow_and_persistence(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(bench,'DB',pathlib.Path(temp)/'test.sqlite'),patch.object(bench,'key',return_value='test-only-key'),patch.object(bench.httpx,'AsyncClient',FakeClient):
   bench.TEMP.clear()
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as client:
    headers={'x-workbench-token':client.get('/api/config').json()['token']}
    self.assertEqual(len(client.get('/api/dataset').json()),66)
    original=next(q for q in bench.QUESTIONS.values() if q['type']=='noul')
    body={'question_id':original['id'],'state':original['state'],'question':original['question'],'model':'jev-1.13.0','repeats':10}
    self.assertEqual(client.post('/api/attempts',json=body).status_code,403)
    result=client.post('/api/attempts',headers=headers,json=body);self.assertEqual(result.status_code,202,result.text);ident=result.json()['id']
    for _ in range(30):
     run=client.get('/api/attempts/'+ident).json()
     if run['status']!='running':break
     time.sleep(.02)
    self.assertEqual(len(run['results']),10)
    self.assertEqual(run['status'],'complete')
    self.assertEqual(client.get('/api/export').json()['attempts'],[])
    with bench.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0],0)
    self.assertEqual(client.patch('/api/attempts/'+ident,headers=headers,json={'saved':True,'note':'reviewed example'}).status_code,200)
    self.assertEqual(len(client.get('/api/export').json()['attempts']),1)
    body['state']='later edit';self.assertNotEqual(client.get('/api/attempts/'+ident).json()['snapshot']['state'],'later edit')
    bench.TEMP.clear()
    self.assertEqual(client.get('/api/attempts/'+ident).json()['note'],'reviewed example')
    client.patch('/api/attempts/'+ident,headers=headers,json={'saved':False,'note':''})
    self.assertEqual(client.get('/api/export').json()['attempts'],[])
    self.assertEqual(client.post('/api/attempts',headers=headers,json=dict(body,repeats=100)).status_code,422)
    self.assertEqual(client.post('/api/attempts',headers={**headers,'origin':'http://untrusted.example'},json=body).status_code,403)
    self.assertNotIn('test-only-key',client.get('/api/export').text)
if __name__=='__main__':unittest.main()

class ReviewTests(unittest.TestCase):
 def test_reviews_validate_persist_and_revise(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(bench,'DB',pathlib.Path(temp)/'reviews.sqlite'):
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as c:
    h={'x-workbench-token':c.get('/api/config').json()['token']}
    q=next(q for q in bench.QUESTIONS.values() if q['type']=='noul');original=json.dumps(q,sort_keys=True)
    body={'dataset':'ref1.2','question_id':q['id'],'revision':0,'status':'corrected','value':False,'note':'人工核查'}
    self.assertEqual(c.post('/api/reviews',json=body).status_code,403)
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,value='false')).status_code,422)
    r=c.post('/api/reviews',headers=h,json=body);self.assertEqual(r.status_code,200,r.text)
    self.assertEqual(c.post('/api/reviews',headers=h,json=body).status_code,409)
    self.assertFalse(c.get('/api/reviews').json()['reviews'][q['id']]['value'])
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,revision=1,status='excluded',note='')).status_code,422)
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,revision=1,status='excluded',note='条件不适用')).status_code,200)
    e=c.get('/api/reviews/export').json();self.assertEqual(len(e['history']),2);self.assertFalse(any(r['question_id']==q['id'] for r in e['accepted_labels']))
    self.assertEqual(original,json.dumps(q,sort_keys=True))
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as c:
    self.assertEqual(c.get('/api/reviews').json()['reviews'][q['id']]['status'],'excluded')

class IntervalTests(unittest.TestCase):
 def test_interval_validation_history_and_export(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(bench,'DB',pathlib.Path(temp)/'interval.sqlite'):
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as c:
    h={'x-workbench-token':c.get('/api/config').json()['token']}
    q=next(q for q in bench.QUESTIONS.values() if q['type']=='noul')
    original=json.dumps(q,sort_keys=True)
    body={'dataset':'ref1.2','question_id':q['id'],'revision':0,'status':'interval','value':{'metric':'noul','lower':.45,'upper':.55},'note':'审核证据不足时的可接受概率'}
    for value in [{'metric':'noul','lower':.6,'upper':.5},{'metric':'noul','lower':-1,'upper':.5},{'metric':'noul','lower':0,'upper':55},{'metric':'noul','lower':True,'upper':1},{'metric':'score','lower':.45,'upper':.55},{'metric':'noul','lower':None,'upper':.55}]:
     self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,value=value)).status_code,422)
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,note='')).status_code,422)
    r=c.post('/api/reviews',headers=h,json=body);self.assertEqual(r.status_code,200,r.text)
    self.assertEqual(r.json()['value'],dict(body['value'],bounds='inclusive'))
    self.assertEqual(c.post('/api/reviews',headers=h,json=body).status_code,409)
    e=c.get('/api/reviews/export').json();self.assertEqual(next(r for r in e['accepted_labels'] if r['question_id']==q['id'])['value']['lower'],.45)
    choice=next(q for q in bench.QUESTIONS.values() if q['type']=='choice')
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,question_id=choice['id'])).status_code,422)
    score=next(q for q in bench.QUESTIONS.values() if q['type']=='score')
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,question_id=score['id'],value={'metric':'score','lower':0,'upper':len(score['question']['criteria'])})).status_code,422)
    self.assertEqual(c.post('/api/reviews',headers=h,json=dict(body,question_id=score['id'],value={'metric':'score','lower':.5,'upper':1})).status_code,200)
    self.assertEqual(json.dumps(q,sort_keys=True),original)
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as c:
    self.assertEqual(c.get('/api/reviews').json()['reviews'][q['id']]['value']['upper'],.55)


class DefaultLabelTests(unittest.TestCase):
 def test_stable_defaults_respect_every_human_decision(self):
  defaults=bench.default_labels({})
  self.assertEqual(len(defaults),730)
  for q in bench.QUESTIONS.values():
   if q['baseline_label']['status']=='review':self.assertNotIn(q['id'],defaults)
   else:
    label=q['baseline_label']['label']
    self.assertEqual(defaults[q['id']]['value'],label.get('score_mean') if q['type']=='score' else label['value'])
  qid=next(iter(defaults))
  for status in ['confirmed','corrected','interval','pending','deferred','excluded']:
   self.assertNotIn(qid,bench.default_labels({qid:{'status':status}}))
  with tempfile.TemporaryDirectory() as temp,patch.object(bench,'DB',pathlib.Path(temp)/'defaults.sqlite'):
   with TestClient(bench.app,base_url='http://127.0.0.1:8766') as c:
    self.assertEqual(len(c.get('/api/reviews').json()['default_labels']),730)
    e=c.get('/api/reviews/export').json()
    self.assertEqual(len(e['accepted_labels']),730)
    self.assertTrue(all(r['source']=='jev_default' for r in e['accepted_labels']))
    self.assertEqual(e['history'],[])
