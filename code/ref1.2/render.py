import pathlib,json,collections,shutil
P=pathlib.Path(__file__).resolve().parent
cases=json.load(open(P/'dataset.json'));summary=json.load(open(P/'summary.json'));labels=json.load(open(P/'labels.json'))
for l in labels:
 pass
stats={'stability_flagged':sum(any(not r.startswith('原题') for r in l['reasons']) for l in labels),'definition_flagged':sum(any(r.startswith('原题') for r in l['reasons']) for l in labels),'both':sum(any(r.startswith('原题') for r in l['reasons']) and any(not r.startswith('原题') for r in l['reasons']) for l in labels)}
summary['review_categories']=stats;(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
# Keep browser payload focused; historical rounds remain in downloadable dataset.json.
view=[]
for g in cases:
 view.append({'id':g['id'],'title':g['title'],'state':g['state'],'questions':[{k:v for k,v in q.items() if k not in ['state','historical_results']} for qs in g['questions'].values() for q in qs]})
(P/'data.js').write_text('const DATA='+json.dumps(view,ensure_ascii=False).replace('<','\\u003c')+';const SUMMARY='+json.dumps(summary,ensure_ascii=False)+';')
(P/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ref1.2 · 五轮基线审核</title><link rel="stylesheet" href="style.css"><header><h1>ref1.2 · 五轮基线审核</h1><p id="totals"></p><p>新增题已标注来源。稳定标签来自 Jev 五轮一致性筛选，尚未人工确认为正确答案。</p><a href="dataset.json" download>完整数据</a> · <a href="review-queue.json" download>审核队列</a> · <a href="label-rules.json">标签规则</a> · <a href="/">进入工作台</a></header><div class="layout"><aside><input id="search" aria-label="搜索场景或问题" placeholder="搜索场景、State 或问题"><select id="status" aria-label="筛选"><option value="review">待审核</option><option value="stable">稳定标签</option><option value="all">全部题目</option></select><select id="type" aria-label="类型"><option value="all">全部类型</option><option value="noul">Noul</option><option value="choice">Choice</option><option value="score">Score</option></select><p id="count"></p><nav id="cases"></nav></aside><main id="main"></main></div><script src="data.js"></script><script src="app.js"></script></html>''')
(P/'style.css').write_text('''*{box-sizing:border-box}body{margin:0;background:#f5f8f6;color:#183d32;font:16px/1.6 system-ui}header{padding:24px 4%;background:white;border-bottom:1px solid #d5e2d9}h1{font-size:28px}.layout{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:1550px;margin:auto;gap:24px;padding:24px}aside{position:sticky;top:12px;height:calc(100vh - 24px);overflow:auto}input,select{width:100%;padding:12px;border:1px solid #ccd9d0;border-radius:8px;margin-bottom:8px;font:inherit}button{cursor:pointer;width:100%;padding:14px;text-align:left;border:1px solid #d2e0d8;border-radius:10px;background:white;margin:5px 0;color:inherit;font:inherit}button.on{background:#dfece3;border-color:#237453}article,.panel{padding:24px;background:white;border:1px solid #d5e2d9;border-radius:14px;margin-bottom:20px}h2,h3{margin:8px 0 18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f4;padding:16px;font:14px/1.6 ui-monospace,monospace}a{color:#17684c}small{color:#647d70}.badge{display:inline-block;border-radius:7px;padding:4px 10px;background:#e8f2eb;margin-right:8px}.warn{background:#fff1d7;color:#83521c;padding:12px;border-radius:8px}.label{font-size:22px;font-weight:700}.rounds{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0}.round{background:#f0f5f1;padding:12px;border-radius:8px;min-width:90px}.round small{display:block}summary{cursor:pointer;margin:12px 0}table{width:100%;border-collapse:collapse}td{border-bottom:1px solid #ddd;padding:10px;overflow-wrap:anywhere}@media(max-width:850px){.layout{display:block;padding:12px}aside{position:static;height:auto;max-height:350px;margin-bottom:20px}article,.panel{padding:16px}}''')
(P/'app.js').write_text(r'''const $=id=>document.getElementById(id),fmt=x=>typeof x==='string'?x:JSON.stringify(x,null,2),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let selected='';
function value(a){if(a.type==='noul')return (a.noul*100).toFixed(1)+'% 是';if(a.type==='choice')return a.choice;return a.score.toFixed(2)+' 分'}
function matches(q,g){return ($('status').value==='all'||q.baseline_label.status===$('status').value)&&($('type').value==='all'||q.type===$('type').value)&&JSON.stringify([g.title,g.state,q.question]).toLowerCase().includes($('search').value.toLowerCase())}
function draw(){const gs=DATA.map(g=>({...g,questions:g.questions.filter(q=>matches(q,g))})).filter(g=>g.questions.length);if(!gs.some(g=>g.id===selected))selected=gs[0]?.id;$('count').textContent=gs.length+' 个场景 · '+gs.reduce((s,g)=>s+g.questions.length,0)+' 道问题';$('cases').innerHTML=gs.map(g=>`<button data-id="${esc(g.id)}" class="${g.id===selected?'on':''}">${esc(g.title)}<br><small>${g.questions.length} 道${$('status').value==='review'?'待审核':''}问题</small></button>`).join('');document.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>{selected=b.dataset.id;draw()});const g=gs.find(g=>g.id===selected);if(!g){$('main').innerHTML='<p>没有符合条件的题目。</p>';return}$('main').innerHTML=`<section class="panel"><h2>${esc(g.title)}</h2><details open><summary>完整 State</summary><pre>${esc(fmt(g.state))}</pre></details></section>`+g.questions.map(q=>{const l=q.baseline_label;const stable=l.status==='stable';const text=l.label?(q.type==='score'?l.label.score_mean.toFixed(3)+' 分 · 最高概率等级 '+l.label.value:q.type==='noul'?(l.label.value?'是':'否'):l.label.value):'待人工审核';return `<article><span class="badge">${q.type.toUpperCase()}</span><small>${q.origin.kind==='project_authored'?'项目新增题':q.origin.kind==='official_definition_reused'?'官方定义 · 新配对':'原有题目'}</small><h3>${esc(fmt(q.question.instructions))}</h3>${q.question.criteria?`<details><summary>${q.type==='score'?'评分等级':'判定标准 / 选项'}</summary><pre>${esc(fmt(q.question.criteria))}</pre></details>`:''}<p class="label">${esc(text)}</p>${stable?'<small>Jev 基线标签 · 未经人工验证</small>':`<div class="warn">${l.reasons.map(esc).join('<br>')}</div>`}<div class="rounds">${q.original_results.map(r=>`<div class="round"><small>第 ${r.round} 次</small><b>${esc(value(r.answer))}</b></div>`).join('')}</div><details><summary>5 次完整原始回答</summary><pre>${esc(fmt(q.original_results))}</pre></details><details><summary>标签统计与筛选原因</summary><pre>${esc(fmt(l))}</pre></details><details><summary>完整问题 JSON 与来源</summary><pre>${esc(fmt({id:q.id,question:q.question,origin:q.origin,sources:q.sources}))}</pre></details></article>`}).join('')}
$('totals').textContent=`${SUMMARY.states} 个场景 · ${SUMMARY.questions} 道题 · ${SUMMARY.answers} 个回答 · ${SUMMARY.statuses.stable} 题稳定 · ${SUMMARY.statuses.review} 题待审核`;
for(const id of ['search','status','type'])$(id).oninput=draw;draw();''')
report=f'''# ref1.2 补题与五轮 Jev 基线

- 66 个 State 均原样保留；原 319 道问题定义和 ID 原样保留。
- 新增 493 个题目配对：480 道项目编写题，13 道复用官方工具路由问题定义。
- 总计 812 题：Noul 314 / Choice 337 / Score 161。每个 State 至少4/4/2，超额原题不删除。
- jev-1.13.0，每个 State 一次请求携带全部题目，重复5次；6并发，每批最多100道不同题；330请求全部成功，4060回答。
- 稳定基线标签730题；审核82题。其中运行稳定性/分布问题{stats['stability_flagged']}题，原题适用性/定义问题{stats['definition_flagged']}题，二者重叠{stats['both']}题。

## 筛选规则（项目设置，并非官方阈值）

Noul：5次均<=0.4或均>=0.6，且概率跨度<=0.10；保留均值概率及布尔判断。位于中间区间的题不自动作为正确标签。
Choice：5次同一选项，每轮该选项概率>=0.70，概率跨度<=0.10。
Score：5次最高概率等级相同，每轮最高等级概率>=0.70，连续score跨度<=0.25；保留平均score和等级，不将连续score误认为纯整数。
稳定性与正确性不同：上述标签来自Jev自身共识，不是独立gold，不能用同源标签宣称Jev真实准确率。
API confidence原样保留，未作为top-label probability使用。

## 额外审核

原日期模板中条件未成立的分支、缺失事件仍被提问，以及冰淇淋三明治原标准解释重叠，均放入审核队列，即使模型输出稳定也不直接定标。此检查仅针对已识别问题，不能宣称所有原题已完成人工质量审核。
短State硬补到10题时，题目主要覆盖显式信息、请求意图、证据充分程度；题目数量不等于10个独立能力维度。跨State共享模板保留，未伪称全是独立任务。
没有通过改写State、颠倒选项或复制同义问法补足数量。同一State新增题中未发现完全重复定义；语义质量仍可在审核页检查。

## 文件

index.html：默认显示82题审核队列，可切换全部/稳定。
dataset.json：全部State、812问题、5次结果、历史结果与来源。
labels.json / stable-labels.json / review-queue.json：标签与审查标记。
responses/：330份完整API响应；run-config.json：请求设置；label-rules.json：阈值。
input.json：运行输入快照；build.py：题目编写定义；run.py：可断点续跑；analyze.py：标签筛选；render.py：可视化生成。

官方接口依据：https://docs.typesafe.ai/api 、 https://docs.typesafe.ai/primitives/score 、 https://docs.typesafe.ai/primitives/choice
'''
(P/'README.md').write_text(report)
D=P.parent.parent/'jev-bench/static/ref1.2';D.mkdir(exist_ok=True)
for f in P.iterdir():
 if f.is_file() and f.suffix in ['.json','.js','.html','.css','.md']:shutil.copy2(f,D/f.name)
shutil.copytree(P/'responses',D/'responses',dirs_exist_ok=True)
print(stats)
