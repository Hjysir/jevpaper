"""Local-only Jev workbench. API keys never leave the server except to TypeSafe."""
import hashlib
import math
import asyncio
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
ENV_FILE = Path('/Users/hujianyi/Desktop/具身智能/jev-workbench/.env')
DATA = ROOT / 'data'
DATA.mkdir(mode=0o700, exist_ok=True)
DB = DATA / 'history.sqlite3'
TOKEN = secrets.token_urlsafe(32)
ACTIVE = set()


def connection():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, created REAL, status TEXT, snapshot TEXT, results TEXT, note TEXT, saved INTEGER)')
        db.execute("UPDATE attempts SET status='interrupted' WHERE status='running'")
        db.execute('CREATE TABLE IF NOT EXISTS label_review_events (id INTEGER PRIMARY KEY AUTOINCREMENT, dataset TEXT NOT NULL, question_id TEXT NOT NULL, revision INTEGER NOT NULL, created REAL NOT NULL, payload TEXT NOT NULL, UNIQUE(dataset,question_id,revision))')
    DB.chmod(0o600)


def key():
    return (dotenv_values(ENV_FILE).get('TYPESAFE_API_KEY') or os.environ.get('TYPESAFE_API_KEY') or '').strip()


def record(row):
    if row is None:
        raise HTTPException(404, '找不到这条记录')
    obj = dict(row)
    obj['request'] = json.loads(obj['request'])
    obj['response'] = json.loads(obj['response']) if obj['response'] else None
    return obj


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    if host not in ('127.0.0.1', 'localhost'):
        return JSONResponse({'detail': '仅允许本机访问'}, 403)
    origin = request.headers.get('origin')
    if origin and origin not in (f'http://{request.headers.get("host")}',):
        return JSONResponse({'detail': '不允许跨站请求'}, 403)
    if request.method in ('POST', 'DELETE', 'PATCH') and request.headers.get('x-workbench-token') != TOKEN:
        return JSONResponse({'detail': '页面会话失效，请刷新后重试'}, 403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


DATASET_PATH = ROOT.parent/'research/ref1.2/dataset.json'
DATASET = json.loads(DATASET_PATH.read_text())
CASES = {g['id']:g for g in DATASET}
QUESTIONS = {q['id']:q for g in DATASET for qs in g['questions'].values() for q in qs}
TASKS=set()
TEMP={}
# One-time handoff preserves temporary attempts during this maintenance restart.
_handoff = DATA / 'maintenance-handoff.json'
if _handoff.exists():
    TEMP.update({r['id']:r for r in json.loads(_handoff.read_text()) if not r['saved']})
    _handoff.unlink()

def update_attempt(ident, **changes):
    r=TEMP.get(ident)
    if r is None:
        with connection() as db:r=attempt(db.execute("SELECT * FROM attempts WHERE id=?",(ident,)).fetchone())
    r.update(changes);TEMP[ident]=r
    if r["saved"]:
        with connection() as db:db.execute("INSERT OR REPLACE INTO attempts VALUES (?,?,?,?,?,?,?)",(ident,r["created"],r["status"],json.dumps(r["snapshot"],ensure_ascii=False),json.dumps(r["results"],ensure_ascii=False),r["note"],1))
    else:
        with connection() as db:db.execute("DELETE FROM attempts WHERE id=?",(ident,))
    return r
SEM=asyncio.Semaphore(3)

@app.get('/')
def home():return FileResponse(ROOT/'static/index.html')

@app.get('/api/config')
def config():return {'configured':bool(key()),'token':TOKEN,'service':'jev-bench','default_model':'jev-1.13.0'}

@app.get('/api/dataset')
def dataset():return DATASET

def attempt(row):
    d=dict(row);d['snapshot']=json.loads(d['snapshot']);d['results']=json.loads(d['results']);return d

@app.get('/api/attempts')
def history():
    with connection() as db:records={r['id']:attempt(r) for r in db.execute('SELECT * FROM attempts').fetchall()}
    records.update(TEMP)
    return sorted(records.values(),key=lambda r:r['created'],reverse=True)

@app.get('/api/attempts/{ident}')
def get_attempt(ident:str):
    if ident in TEMP:return TEMP[ident]
    with connection() as db:r=db.execute('SELECT * FROM attempts WHERE id=?',(ident,)).fetchone()
    if not r:raise HTTPException(404,'记录不存在')
    return attempt(r)

def validate_snapshot(body):
    if not isinstance(body,dict):raise HTTPException(422,'请求应为对象')
    original=QUESTIONS.get(body.get('question_id'))
    if not original:raise HTTPException(422,'请选择题库中的问题')
    state=body.get('state');q=body.get('question')
    if not isinstance(state,(str,dict,list)) or not state:raise HTTPException(422,'请输入有效 State')
    if not isinstance(q,dict) or q.get('type') not in ('noul','choice','score'):raise HTTPException(422,'问题类型不正确')
    if not isinstance(q.get('instructions'),(str,dict,list)) or not q['instructions']:raise HTTPException(422,'问题说明不能为空')
    if set(q)-{'type','instructions','criteria','weight'}:raise HTTPException(422,'问题包含未知字段')
    if q['type']=='choice' and (not isinstance(q.get('criteria'),dict) or not 2<=len(q['criteria'])<=255):raise HTTPException(422,'Choice 需要 2–255 个选项')
    if q['type']=='score' and (not isinstance(q.get('criteria'),list) or not 2<=len(q['criteria'])<=10):raise HTTPException(422,'Score 需要 2–10 个等级')
    if q['type']=='noul' and 'criteria' in q and not isinstance(q['criteria'],dict):raise HTTPException(422,'Noul 判定标准应为对象')
    model=body.get('model','jev-1.13.0')
    if not isinstance(model,str) or not model.startswith('jev-') or len(model)>80:raise HTTPException(422,'模型名称无效')
    repeats=body.get('repeats',1)
    if type(repeats) is not int or repeats not in (1,10):raise HTTPException(422,'仅支持 1 次或 10 次')
    baseline_round=body.get('baseline_round',0)
    if type(baseline_round)is not int or not 0<=baseline_round<len(original['original_results']):raise HTTPException(422,'基线轮次无效')
    for field in ['goal','invariants','note']:
        if not isinstance(body.get(field,''),str) or len(body.get(field,''))>10000:raise HTTPException(422,'备注格式无效')
    return {'question_id':original['id'],'state':state,'question':q,'model':model,'repeats':repeats,
      'baseline_round':baseline_round,'goal':body.get('goal',''),'invariants':body.get('invariants',''),
      'original':original,'task_definition_changed':q!=original['question'],
      'baseline_context':'历史基线为同一 State 多题调用；本次只运行目标题，调用上下文不同。'}

async def execute(ident,snapshot,api_key):
    results=[]
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=20),follow_redirects=False) as client:
            async def once(index):
                async with SEM:
                    start=time.perf_counter()
                    try:
                        response=await client.post('https://api.typesafe.ai/v1/systemone',headers={'Authorization':'Bearer '+api_key},json={'model':snapshot['model'],'state':snapshot['state'],'questions':{'target':snapshot['question']}})
                        if response.status_code!=200:raise ValueError('API 返回 HTTP '+str(response.status_code)+'，未自动重试')
                        data=response.json()
                        if set(data.get('answers',{}))!={'target'} or data['answers']['target'].get('type')!=snapshot['question']['type']:raise ValueError('响应缺少匹配答案')
                        r={'round':index+1,'status':'complete','response':data,'elapsed':time.perf_counter()-start}
                    except Exception as e:
                        msg=str(e) if isinstance(e,ValueError) else '连接异常或超时，远端结果未知，未自动重试'
                        r={'round':index+1,'status':'error','error':msg.replace(api_key,'[隐藏]'),'elapsed':time.perf_counter()-start}
                    results.append(r)
                    update_attempt(ident,results=sorted(results,key=lambda x:x['round']))
            await asyncio.gather(*(once(i) for i in range(snapshot['repeats'])))
        status='complete' if all(r['status']=='complete' for r in results) else 'partial_error'
        update_attempt(ident,status=status)
    finally:ACTIVE.discard(ident)

@app.post('/api/attempts',status_code=202)
async def start(request:Request):
    raw=await request.body()
    if len(raw)>1500000:raise HTTPException(413,'输入过大')
    try:body=json.loads(raw)
    except ValueError:raise HTTPException(422,'JSON 无法解析')
    s=validate_snapshot(body)
    if not key():raise HTTPException(400,'本地 Jev 凭据未配置')
    if len(ACTIVE)>=3:raise HTTPException(409,'已有 3 个尝试运行中，请稍等')
    ident=uuid.uuid4().hex
    TEMP[ident]={'id':ident,'created':time.time(),'status':'running','snapshot':s,'results':[],'note':body.get('note',''),'saved':0}
    ACTIVE.add(ident);task=asyncio.create_task(execute(ident,s,key()));TASKS.add(task);task.add_done_callback(TASKS.discard)
    return {'id':ident}

@app.patch('/api/attempts/{ident}')
async def annotate(ident:str,request:Request):
    body=await request.json()
    if not isinstance(body.get('note',''),str) or len(body.get('note',''))>10000:raise HTTPException(422,'备注过长')
    r=get_attempt(ident)
    if r['status']=='running':raise HTTPException(409,'请等待运行完成再保存')
    update_attempt(ident,note=body.get('note',''),saved=int(bool(body.get('saved'))))
    return {'ok':True}

@app.get('/api/export')
def export():return {'dataset':'ref1.2-66-states-812-questions','attempts':[r for r in history() if r['saved']]}


REVIEW_VERSION = 'ref1.2'

def question_fingerprint(q):
    return hashlib.sha256(json.dumps({'state':q['state'],'question':q['question']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def latest_reviews():
    with connection() as db:
        rows=db.execute('SELECT payload FROM label_review_events WHERE dataset=? ORDER BY id',(REVIEW_VERSION,)).fetchall()
    out={}
    for row in rows:
        item=json.loads(row['payload']);out[item['question_id']]=item
    return out

def default_labels(current):
    # Explicit human records, including pending/deferred/excluded, always take priority.
    out={}
    for q in QUESTIONS.values():
        baseline=q.get('baseline_label',{})
        if q['id'] in current or baseline.get('status')!='stable':continue
        label=baseline.get('label')
        if label is None:continue
        value=label.get('score_mean') if q['type']=='score' else label.get('value')
        out[q['id']]={'question_id':q['id'],'type':q['type'],'value':value,'source':'jev_default','note':'按用户规则默认采用五轮稳定 Jev 基线；未作人工验证','fingerprint':question_fingerprint(q)}
    return out

@app.get('/api/reviews')
def reviews():
    current=latest_reviews()
    return {'dataset':REVIEW_VERSION,'reviews':current,'default_labels':default_labels(current)}

@app.post('/api/reviews')
async def save_review(request:Request):
    body=await request.json()
    if not isinstance(body,dict):raise HTTPException(422,'审核内容格式不正确')
    q=QUESTIONS.get(body.get('question_id',''))
    if q is None:raise HTTPException(422,'题目不存在')
    if body.get('dataset')!=REVIEW_VERSION:raise HTTPException(409,'数据版本已变更，请刷新')
    status=body.get('status');note=body.get('note','');revision=body.get('revision')
    if status not in ['confirmed','corrected','interval','excluded','deferred','pending']:raise HTTPException(422,'审核状态不正确')
    if not isinstance(note,str) or len(note)>10000:raise HTTPException(422,'备注过长或格式不正确')
    if status in ['corrected','interval','excluded','deferred'] and not note.strip():raise HTTPException(422,'请填写修改、排除或暂缓的原因')
    if type(revision)is not int or revision<0:raise HTTPException(422,'审核版本不正确')
    candidate=q.get('baseline_label',{}).get('candidate');value=None
    if status=='confirmed':
        if candidate is None:raise HTTPException(422,'没有可确认的候选标签，请手动填写')
        value=candidate.get('score_mean') if q['type']=='score' else candidate.get('value')
    elif status=='corrected':value=body.get('value')
    if status=='interval':
        value=body.get('value')
        if q['type'] not in ['noul','score'] or not isinstance(value,dict):raise HTTPException(422,'区间只适用于 Noul 概率或 Score 分数')
        lower=value.get('lower');upper=value.get('upper');metric='noul' if q['type']=='noul' else 'score'
        maximum=1 if q['type']=='noul' else len(q['question']['criteria'])-1
        if value.get('metric')!=metric or any(type(v) not in [int,float] or not math.isfinite(v) for v in [lower,upper]) or not 0<=lower<=upper<=maximum:raise HTTPException(422,'区间上下限或单位不正确')
        value={'metric':metric,'lower':lower,'upper':upper,'bounds':'inclusive'}
    if status in ['confirmed','corrected']:
        if q['type']=='noul' and type(value)is not bool:raise HTTPException(422,'Noul 标签应为是或否')
        if q['type']=='choice' and (not isinstance(value,str) or value not in q['question']['criteria']):raise HTTPException(422,'请选择原题中的选项')
        if q['type']=='score' and (type(value) not in [int,float] or not math.isfinite(value) or not 0<=value<=len(q['question']['criteria'])-1):raise HTTPException(422,'评分不在原题等级范围内')
    item={'dataset':REVIEW_VERSION,'question_id':q['id'],'status':status,'value':value,'type':q['type'],'note':note.strip(),'revision':revision+1,'reviewed_at':time.time(),'source':'human_review','fingerprint':question_fingerprint(q),'original':{'state':q['state'],'question':q['question']},'jev_baseline_label':q.get('baseline_label')}
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        last=db.execute('SELECT MAX(revision) FROM label_review_events WHERE dataset=? AND question_id=?',(REVIEW_VERSION,q['id'])).fetchone()[0] or 0
        if last!=revision:raise HTTPException(409,'该题审核已被另一页面更新，请刷新后再保存')
        db.execute('INSERT INTO label_review_events(dataset,question_id,revision,created,payload) VALUES(?,?,?,?,?)',(REVIEW_VERSION,q['id'],revision+1,item['reviewed_at'],json.dumps(item,ensure_ascii=False)))
    return item

@app.get('/api/reviews/export')
def export_reviews():
    current=latest_reviews()
    with connection() as db:history=[json.loads(r['payload']) for r in db.execute('SELECT payload FROM label_review_events WHERE dataset=? ORDER BY id',(REVIEW_VERSION,))]
    defaults=default_labels(current)
    accepted=[{'question_id':r['question_id'],'type':r['type'],'value':r['value'],'source':'human_review','note':r['note']} for r in current.values() if r['status'] in ['confirmed','corrected','interval']]
    return {'dataset':REVIEW_VERSION,'default_policy':'stable Jev labels apply only where no human review record exists; special review questions require human decisions','reviews':list(current.values()),'history':history,'default_labels':list(defaults.values()),'accepted_labels':accepted+list(defaults.values())}

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
