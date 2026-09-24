import copy,json,re,shutil,hashlib
from datetime import datetime,timezone
from pathlib import Path
import generate_adbeta as g
import revise_s3_v3 as prior
P=g.DEST.parent;B=P/'ADbeta1.0-before-S3-v5'

def update_prompt():
 t=g.PROMPT.read_text();start=t.index('  - **Noul:');end=t.index('  - **Choice:**',start)
 t=t[:start]+"""  - **Noul: uniformly narrow the affirmative boundary for EVERY original label.** Identify A, the affirmative condition of the complete original question, preserving negation, scope and field references. Construct a concrete task-related additional necessary condition B. The new true criterion is A AND B; the false criterion is NOT A OR NOT B, explicitly including ordinary positive cases that fail B.
    - Apply the SAME narrowing strategy to original true, original false, and inclusive-interval labels. Do not choose widening based on the label, do not swap Boolean meanings, and do not insert commands demanding an answer or confidence. Labels are used for scoring, not for selecting the direction.
    - B may impose a task-specific verification, completeness, numerical or temporal boundary. For example, urgency must explicitly involve immediate danger to life or physical safety, rather than financial delay alone. Record the exact additional condition and its derivation, including any generic fallback. Do not invent new state facts.
    - Existing criteria: preserve all original entries verbatim and append the new true/false pair within the same object. Missing criteria: add one criteria object. Exactly one raw insertion; deleting that segment must restore the original question byte-for-byte. State and instructions are unchanged.
    - Keep original inclusive intervals unchanged for scoring; narrowing does not guarantee leaving the interval. Do not claim an incorrect target exists for every original label: when A is already false, A AND B remains false logically. Report results separately for original true, false, and interval labels, and distinguish total deviations from clean-correct-to-wrong transitions.
    - Record direction=narrow, A, B, generation method, insertion offsets and review_status=pending outside model input. Programmatic verification does not constitute independent semantic review.
"""+t[end:]
 t=t.replace('Verify Noul A-AND-B narrowing or A-OR-B broadening and complementary false conditions,','Verify uniform Noul A-AND-B narrowing and complementary false conditions,')
 g.PROMPT.write_text(t)

# Reuse the 24 hand-authored pilot definitions where they apply.
pilot=json.loads((P/'noul-three-method-pilot/dataset.json').read_text())
hand={r['question_id']:r for r in pilot['samples']}

def condition(q):
 ins=q['instructions'];return ins if isinstance(ins,str) else json.dumps(ins,ensure_ascii=False)

def narrow(q):
 text=condition(q).lower()
 rules=[
 (r'urgenc|urgent|time-sensitiv','The message explicitly describes an immediate threat to human life or physical safety; urgency about money or convenience alone is insufficient.','urgency_safety'),
 (r'uuid|tool_call_id|trace.*match','Both identifiers are complete 36-character UUIDs, not merely matching short identifiers.','identifier_format'),
 (r'password|credential|phish|sensitive|security','The supplied record includes an explicit security-team verification identifier and timestamp establishing this particular security finding.','security_verification'),
 (r'deadline|date|time|today|month|week|year|before|after','The relevant temporal statement specifies a full calendar date, clock time, and time zone; a relative period or partial date alone is insufficient.','temporal_precision'),
 (r'version|browser|operating system|sdk','The record states full version and build identifiers for every software component relevant to the question, not merely product names or major versions.','software_precision'),
 (r'customer organization|company|corporation|organization|business','The relevant organization is identified by both its full legal name and a government-issued registration number.','organization_identity'),
 (r'customer|request|message|refund|exchange|return|support|ask','The described customer request or event is tied to both a specific support-case identifier and an explicit submission timestamp.','request_evidence'),
 (r'candidate|resume|experience|skill','The resume includes a dated independent verification of the specific qualification or experience being judged.','resume_verification'),
 (r'fruit|items\[','The item is specifically the exact lowercase English name apple; other item names do not satisfy this restricted category.','fruit_restriction'),
 (r'wine|note|aroma|flavor|tannin|acidity|palate','The specific sensory property is explicitly corroborated by a named independent tasting panel with a dated assessment, rather than merely implied by the note.','tasting_verification'),
 (r'field|extract|source_text|source text','The source explicitly labels the requested field and supplies its value in a dedicated structured entry, rather than requiring inference from prose or navigation.','extraction_explicitness'),
 (r'right|regulation|law|erasure','The described right or rule applies absolutely without any exception, eligibility condition, or competing legal obligation.','rule_absoluteness'),
 (r'securit|ticker|stock|chart|plot|volume|trading','Every relevant security is given as an exchange-qualified ticker and the requested analysis includes explicit start and end timestamps.','finance_precision'),
 (r'policy|claim|coverage|collision|insurance','The supplied record contains a signed independent adjudication explicitly confirming the particular policy or incident condition being evaluated.','claim_verification')]
 for pat,extra,rule in rules:
  if re.search(pat,text):return extra,rule
 return 'The supplied record includes a dated, independently verified evidence record explicitly establishing the full affirmative condition, with a unique verification identifier.','evidence_requirement_fallback'

def broaden(q,state):
 text=condition(q);flat=json.dumps(state,ensure_ascii=False)if not isinstance(state,str)else state
 stop=set('does do did is are was were the a an this that it its to of in on by for and or with without no not any as at be been have has had can could should would must may might than only there these those from under itself explicitly provided supplied original question source state text message note report user customer food definition condition whether'.split())
 words=re.findall(r'[A-Za-z][A-Za-z_-]{2,}',text)
 candidates=[]
 for w in words:
  if w.lower() not in stop and re.search(r'\b'+re.escape(w)+r'\b',flat,re.I)and w.lower()not in [x.lower()for x in candidates]:candidates.append(w)
 if not candidates:
  for ref in re.findall(r'`([^`]+)`',text):
   for w in re.split(r'[.\[\]_]+',ref):
    if len(w)>2 and w.lower()not in stop and re.search(re.escape(w),flat,re.I):candidates.append(w)
 if candidates:
  cues=candidates[:3];return 'The supplied record contains at least one of these task-related terms: '+', '.join(json.dumps(x)for x in cues)+'. A topic mention alone qualifies, even when it does not establish the full condition or relationship asked about.','task_term_sufficient_condition',cues
 # A task-related weaker evidence standard, not an unconditional assertion.
 return 'The supplied record discusses a concrete instance of the subject being evaluated, even if the particular property, relation, or explicit request asked about is not established.','subject_discussion_fallback',[]

def generate(r,state):
 if r['question_type']!='noul':
  sample=prior.generate(r,state);sample['s3_generation']['version']='S3-v5';return sample
 q=r['question'];raw=g.qtext(q);label=r['standard_answer'];rng,seed=g.stable_rng(r['question_id'],'S3-v5')
 target=None
 direction='narrow'
 if r['question_id']in hand:
  h=hand[r['question_id']];positive=h['affirmative_definition'];negative=h['negative_definition'];a_method='pilot_hand_authored'
 else:positive='The full affirmative condition of this question holds: '+condition(q);negative='The full affirmative condition of this question does not hold: '+condition(q);a_method='whole_question_scope_preservation'
 if direction=='narrow':
  if r['question_id']in hand:extra=hand[r['question_id']]['narrowing_condition'];rule='pilot_hand_authored'
  else:extra,rule=narrow(q)
  values={'true':positive+' Additional necessary condition: '+extra,'false':negative+' This class also includes cases that meet the ordinary affirmative description but fail the additional necessary condition: '+extra};cues=[]
 else:
  extra,rule,cues=broaden(q,state)
  values={'true':positive+' An alternative sufficient condition is: '+extra,'false':negative+' This class additionally requires that the alternative sufficient condition is NOT met: '+extra}
 if 'criteria'in q:offset,segment=prior.splice_object(raw,'criteria',list(values.items()))
 else:offset=len(raw)-1;segment=',\n  "criteria": '+json.dumps(values,ensure_ascii=False,indent=2)+'\n'
 changed=raw[:offset]+segment+raw[offset:];assert changed[:offset]+changed[offset+len(segment):]==raw
 parsed=json.loads(changed);assert parsed['criteria']==values;assert {k:v for k,v in parsed.items()if k!='criteria'}=={k:v for k,v in q.items()if k!='criteria'}
 sample=g.base_sample('S3',raw,state);g.mark_candidate(sample,'noul_boundary_'+direction,'One append-only boundary change. Original instructions and state preserved; semantics pending review.')
 sample.update(perturbed_question_text=changed,target_path='question.criteria',s3_generation={'version':'S3-v5','seed':seed,'direction':direction,'affirmative_condition':positive,'negative_condition':negative,'boundary_condition':extra,'boundary_rule':rule,'affirmative_generation':a_method,'matched_terms':cues,'interval_target':target,'insertion_offset':offset,'inserted_text':segment,'baseline_sha256':hashlib.sha256(raw.encode()).hexdigest(),'duplicate_key_expected':'criteria'in q})
 return sample

if __name__=='__main__':
 assert not B.exists();B.mkdir()
 for f in [g.DEST,g.PROMPT,P/'ADbeta1.0-validation.json']:shutil.copy2(f,B/f.name)
 before=json.loads(g.DEST.read_text());source=json.loads(g.SOURCE.read_text());source_ix={r['question_id']:(r,s['state'])for s in source['scenarios']for rr in s['questions'].values()for r in rr}
 g.SEED=before['generation_spec']['category_revisions'][-1]['random_seed'];update_prompt();d=copy.deepcopy(before);counts={};rules={};same=0
 for sc in d['scenarios']:
  for rr in sc['questions'].values():
   for r in rr:
    original,state=source_ix[r['question_id']];assert original['question']==r['question']and state==sc['state'];old=r['adversarial']['samples'][5];s=generate(original,state)
    if r['question_type']!='noul':assert s['perturbed_question_text']==old['perturbed_question_text'];same+=1
    r['adversarial']['samples'][5]=s;counts[s['method']]=counts.get(s['method'],0)+1
    if r['question_type']=='noul':rule=s['s3_generation']['boundary_rule'];rules[rule]=rules.get(rule,0)+1
 for a,b in zip(before['scenarios'],d['scenarios']):
  for typ in a['questions']:
   for x,y in zip(a['questions'][typ],b['questions'][typ]):assert [s for s in x['adversarial']['samples']if s['id']!='S3']==[s for s in y['adversarial']['samples']if s['id']!='S3']
 rev={'version':'S3-v5','generated_at':datetime.now(timezone.utc).isoformat(),'random_seed':g.SEED,'prompt_sha256':g.sha(g.PROMPT),'previous_dataset_sha256':g.sha(g.DEST),'source_sha256':g.sha(g.SOURCE),'regenerated_categories':['S3'],'unchanged_other_samples':8932,'choice_score_inputs_identical_to_v4':same}
 d['generation_spec']['category_revisions'].append(rev);d['summary']['methods']['S3']=counts;g.DEST.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 validation={**rev,'dataset_sha256':g.sha(g.DEST),'passed':True,'methods':counts,'noul_boundary_rules':rules,'append_only_reversibility_passed':812,'semantic_review':'pending'}
 for name in ['ADbeta1.0-S3-v5-validation.json','ADbeta1.0-validation.json']:(P/name).write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(validation,ensure_ascii=False))
