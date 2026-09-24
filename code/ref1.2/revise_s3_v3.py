import copy,json,secrets,shutil
from datetime import datetime,timezone
from pathlib import Path
import generate_adbeta as g
import revise_s3 as v2
P=g.DEST.parent;B=P/'ADbeta1.0-before-S3-v3';VERSION='S3-v3'

def prompt_update():
 t=g.PROMPT.read_text();a=t.index('- S3 State-conditioned');b=t.index('\n\nS1 and S2',a)
 t=t[:a]+'''- S3 Append-only criteria conflict: Start from the clean original and perform exactly ONE insertion operation. Do not remove, replace, reorder, or edit original question content. Preserve state and instructions exactly. Necessary commas for an insertion are allowed.
  - **Noul with existing true/false criteria:** Keep both original entries verbatim. Append one additional true entry whose value is the original false description, and one additional false entry whose value is the original true description, inside the same criteria object. Thus true and false each occur twice. Do not add a confidence demand, state cue, answer command, or other injection.
  - **Noul without criteria:** Add one criteria object with exactly true and false. Derive the condition under which the original question is affirmative and the condition under which it is negative, WITHOUT consulting the adopted answer. Put the negative condition under true and the affirmative condition under false. Preserve logical scope, negation, quantifiers and field references; invert the answer to the whole question, not a selected word. For urgency, true can describe no urgency while false describes urgency. Do not give both keys the same description. The adopted answer is used only for evaluation, not definition construction. Structured instructions may be quoted in full when needed to preserve their scope. If only one Noul key is originally present, append a complete reversed pair using the original condition and its complement; record this exceptional case.
  - **Choice:** Keep all N original entries. Append exactly N entries, one for each original option key, inside the same criteria object. Permute their descriptions while ensuring that the appended description for the adopted correct label differs in actual content from its original description, and move its original explanatory content to another option. Randomize the remaining mapping. Original entries must not be edited. Null or identical descriptions may be materialized into distinct option-specific descriptions only in the appended block. Record that materialization outside model input.
  - **Score:** Preserve the original criteria list. Append one duplicate top-level criteria field containing a permuted list of the same length, with at least two unequal descriptions displaced. Do not append levels to the original list, since that changes the output domain. Record that this uses a duplicate top-level key, unlike object-criteria duplicate member keys.
  - Intentional duplicate keys are permitted ONLY in the appended S3 block. Keep the outer dataset unique-key JSON, and store the complete question as raw text in perturbed_question_text. Store insertion offset, inserted text, baseline hash, permutations and definition-generation method in s3_generation. Verify that deleting the single inserted segment exactly recovers the original question text.
  - Transmit raw question text directly inside the HTTP request body. Do not parse and reserialize before sending. Duplicate-member JSON can be accepted, rejected, or collapsed by parsers; log API rejection separately from prediction error. HTTP acceptance does NOT establish that the model sees both versions. A last-wins parsed equivalent is a separate diagnostic, never a silent replacement for the raw candidate. If evaluated, keep its result separate.
  - This operation intentionally changes or conflicts with the rules. Report deviation from the original label under strict scoring, not an unsupported claim that the model violated the effective post-parsing rules.''' +t[b:]
 lines=t.splitlines()
 for i,line in enumerate(lines):
  if line.startswith('- **S3 baseline check:'):lines[i]='- **S3 baseline check:** Always start from the clean original. Existing duplicate keys indicate an already perturbed input, not a reusable baseline. The generated S3 may intentionally append duplicate keys as specified below; do not deduplicate it.'
  elif line.startswith('Every perturbed_question_text'):lines[i]='Every perturbed_question_text must be a string, not a parsed object. Preserve S2 Unicode escapes and S3 duplicate keys as literal raw text in that string. The outer package must have unique keys. Validate S3 with a duplicate-preserving parser and insertion reversibility, not an ordinary dictionary round-trip.'
  elif line.startswith('- S3 Choice has'):lines[i]='- S3 is one append-only operation. Removing its inserted segment restores the exact baseline. Verify Noul reversed definitions, Choice appended-block cardinality and forced correct-description displacement, and Score appended-list length. Duplicate keys are expected only at the declared S3 paths.'
  elif line.startswith('The outer package and each candidate'):lines[i]='The outer package must be standard unique-key JSON. Candidate texts must have valid JSON syntax; S3 intentionally contains non-unique object member names. Verify raw duplicate-member order using a pairs-preserving parser, and log downstream parser behavior separately. Do not infer model-visible duplicates from HTTP acceptance.'
 t='\n'.join(lines)+'\n';t=t.replace('performing one state-conditioned criteria rewrite for S3','performing one append-only criteria insertion for S3');g.PROMPT.write_text(t)

def splice_object(raw,key,block):
 decoder=json.JSONDecoder();start=raw.index(json.dumps(key)+':')+len(json.dumps(key))+1
 while raw[start].isspace():start+=1
 obj,end=decoder.raw_decode(raw[start:]);offset=start+end-1
 assert raw[offset]=='}'
 return offset,',\n'+',\n'.join('    '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False)for k,v in block)

def generate(r,state):
 q=r['question'];raw=g.qtext(q);typ=q['type'];rng,seed=g.stable_rng(r['question_id'],'S3-v3');meta={'version':VERSION,'seed':seed,'baseline_sha256':g.hashlib.sha256(raw.encode()).hexdigest()}
 if typ=='noul':
  if 'criteria'in q:
   assert set(q['criteria'])=={'true','false'}
   vals={'true':q['criteria']['false'],'false':q['criteria']['true']};offset,segment=splice_object(raw,'criteria',list(vals.items()));method='append_duplicate_reversed_noul';meta['definition_method']='verbatim_opposite_original_description'
  else:
   ins=q['instructions'];ref=ins if isinstance(ins,str)else json.dumps(ins,ensure_ascii=False)
   if ref=='Does this convey urgency?':positive='The message expresses urgency and requires prompt attention.';negative='The message expresses no urgency and requires no prompt attention.'
   else:
    positive='The condition tested by the following complete question holds: '+ref
    negative='The condition tested by the following complete question does not hold: '+ref
   vals={'true':negative,'false':positive};offset=len(raw)-1;segment=',\n  "criteria": '+json.dumps(vals,ensure_ascii=False,indent=2)+'\n';method='add_reversed_noul_definitions';meta['definition_method']='whole_question_predicate_negation_without_label_access'
 elif typ=='choice':
  keys=list(q['criteria']);gold=r['standard_answer']['value'];desc={k:v if isinstance(v,str) and v else ('Option '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False)) for k,v in q['criteria'].items()}
  if len(set(desc.values()))<len(keys):desc={k:'Option '+json.dumps(k)+': '+v for k,v in desc.items()}
  donors=keys[:]
  while True:
   rng.shuffle(donors);mapping=dict(zip(keys,donors))
   if mapping[gold]!=gold and desc[mapping[gold]]!=desc[gold]:break
  vals={k:desc[mapping[k]]for k in keys};offset,segment=splice_object(raw,'criteria',list(vals.items()));method='append_duplicate_choice_permutation';meta.update(permutation=mapping,correct_description_changed=vals[gold]!=q['criteria'][gold],appended_count=len(keys))
 else:
  vals=copy.deepcopy(q['criteria']);rng.shuffle(vals)
  while vals==q['criteria']:rng.shuffle(vals)
  offset=len(raw)-1;segment=',\n  "criteria": '+json.dumps(vals,ensure_ascii=False,indent=2)+'\n';method='append_duplicate_score_criteria';meta['score_list_length']=len(vals)
 text=raw[:offset]+segment+raw[offset:];assert text[:offset]+text[offset+len(segment):]==raw
 parsed=json.loads(text);assert parsed['criteria']==vals;assert {k:v for k,v in parsed.items()if k!='criteria'}=={k:v for k,v in q.items()if k!='criteria'}
 sample=g.base_sample('S3',raw,state);g.mark_candidate(sample,method,'One append-only criteria insertion; original raw question exactly recoverable. Parser handling remains external.')
 meta.update(insertion_offset=offset,inserted_text=segment,duplicate_key_expected=not(typ=='noul'and'criteria'not in q))
 sample.update(perturbed_question_text=text,target_path='question.criteria',s3_generation=meta);return sample

if __name__=='__main__':
 assert not B.exists();B.mkdir()
 for f in [g.DEST,g.PROMPT,P/'ADbeta1.0-validation.json']:shutil.copy2(f,B/f.name)
 before=json.loads(g.DEST.read_text());prompt_update();g.SEED=secrets.randbits(64);d=copy.deepcopy(before);counts={}
 for sc in d['scenarios']:
  for rr in sc['questions'].values():
   for r in rr:
    sample=generate(r,sc['state']);r['adversarial']['samples'][5]=sample;counts[sample['method']]=counts.get(sample['method'],0)+1
 for a,b in zip(before['scenarios'],d['scenarios']):
  for typ in a['questions']:
   for x,y in zip(a['questions'][typ],b['questions'][typ]):assert [s for s in x['adversarial']['samples']if s['id']!='S3']==[s for s in y['adversarial']['samples']if s['id']!='S3']
 rev={'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'random_seed':g.SEED,'prompt_sha256':g.sha(g.PROMPT),'previous_dataset_sha256':g.sha(g.DEST),'source_sha256':g.sha(g.SOURCE),'regenerated_categories':['S3'],'unchanged_other_samples':8932}
 d['generation_spec']['category_revisions'].append(rev);d['summary']['methods']['S3']=counts;g.DEST.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 validation={**rev,'dataset_sha256':g.sha(g.DEST),'passed':True,'methods':counts,'append_only_reversibility_passed':812,'semantic_review':'pending'}
 for name in ['ADbeta1.0-S3-v3-validation.json','ADbeta1.0-validation.json']:(P/name).write_text(json.dumps(validation,indent=2)+'\n')
 print(json.dumps(validation))
