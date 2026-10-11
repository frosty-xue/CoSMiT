"""Evaluate local baselines and CoSMiT core with an explicit recorded-test adapter.

Predictions do not read reference labels. Scoring is a separate command.
Recorded tests are reused; this is not end-to-end inference from arbitrary tests.
"""
import argparse, ast, hashlib, importlib.util, json, os, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from cosmit.engine.certification import Property, Candidate, Observation, certify

def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def signature(r):return {k:r[k] for k in ['status','phase','operation_count','first_observation','error']}

def static_assertions(path):
 result=[]
 for n in ast.walk(ast.parse(path.read_text(encoding='utf8'))):
  if isinstance(n,ast.Assert):result.append((n.lineno,ast.unparse(n),isinstance(n.test,ast.Constant) and n.test.value is True))
  elif isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert'):
   vacuous=n.func.attr=='assertTrue' and len(n.args)==1 and isinstance(n.args[0],ast.Constant) and n.args[0].value is True
   result.append((n.lineno,ast.unparse(n),vacuous))
 return result

def predict(data,out):
 import numpy as np
 out.mkdir(parents=True,exist_ok=False)
 public=data/'evaluation-inputs'
 for rel,h in read(public/'SHA256.json').items():assert sha(public/rel)==h,rel
 for rel,h in read(data/'frozen-SHA256.json').items():assert sha(data/rel)==h,rel
 # Match bodies to recorded campaigns by hashes, not the answer-key mapping.
 routes=[]
 for folder in data.iterdir():
  if not (folder/'executions.json').exists():continue
  rows=read(folder/'executions.json')['records']
  for reg in read(folder/'retained/registration.json'):
   cid=reg['case_id']
   routes.append((sha(folder/f'retained/{cid}-source.py'),sha(folder/f'retained/{cid}-target.py'),cid,rows,folder/'executions.json'))
 predictions=[];audit=[];consumed={}
 for sample in read(public/'samples.json'):
  sid=sample['sample_id'];source=public/sample['files']['source-test.py'];target=public/sample['files']['target-test.py']
  matches=[x for x in routes if x[:2]==(sha(source),sha(target))];assert len(matches)==1
  _,_,cid,rows,path=matches[0];consumed[str(path)]=sha(path)
  rows=[r for r in rows if r['case_id']==cid]
  ix={(r['side'],r['mode'],r['repeat']):r for r in rows};assert len(ix)==30
  for side in ['source','target']:
   for mode in ['original','observe','reinject','wrong-shape','wrong-value']:
    rs=[ix[side,mode,i] for i in range(3)]
    assert all(signature(r)==signature(rs[0]) for r in rs)
  normal=all(ix[s,'original',i]['status']=='passed' for s in ['source','target'] for i in range(3))
  base=all(ix[s,m,i]['status']=='passed' and (m=='original' or ix[s,m,i]['operation_count']>0) for s in ['source','target'] for m in ['original','observe','reinject'] for i in range(3))
  for s in ['source','target']:
   for i in range(3):base &= ix[s,'observe',i]['first_observation']==ix[s,'reinject',i]['first_observation']
  assertions=static_assertions(target)
  result={'sample_id':sid,'predictions':{'normal-execution':'preserved' if normal else 'undetermined','assertion-present':'preserved' if assertions else 'violated','nonvacuous-assertion-present':'preserved' if any(not a[2] for a in assertions) else 'violated'}}
  # This comparator uses only unperturbed operation observations, not test outcomes.
  eq=all(ix['source','observe',i]['first_observation']==ix['target','observe',i]['first_observation'] for i in range(3))
  result['predictions']['operation-observation-equality']='preserved' if base and eq else 'undetermined'
  gates=[];eligible=[]
  for clause in sample['obligations']:
   mode='wrong-'+clause
   accepted=base;reason=[]
   for i in range(3):
    s,t=ix['source',mode,i],ix['target',mode,i]
    if s['status']!='assertion-rejected':accepted=False;reason.append('source-not-assertion-rejected')
    if t['status'] not in ['assertion-rejected','passed']:accepted=False;reason.append('target-infrastructure-or-runtime-error')
    if s['first_observation']!=t['first_observation']:accepted=False;reason.append('unequal-delivered-observation')
    for r in [s,t]:
     if not r['first_observation']:accepted=False;reason.append('missing-observation');continue
     o=r['first_observation'][0];a=np.asarray(o['native']['values'],dtype=o['native']['dtype']);z=np.asarray(o['delivered']['values'],dtype=o['delivered']['dtype'])
     expected=a.reshape((1,)+a.shape) if clause=='shape' else (a+(np.abs(a)*.2+10)).astype(a.dtype)
     if not (np.array_equal(z,expected) and z.shape==expected.shape):accepted=False;reason.append('perturbation-mismatch')
     if r['status']=='assertion-rejected' and not any(f['file'].endswith(('-source-observed.py','-target.py')) for f in r['frames']):accepted=False;reason.append('unattributed-rejection')
   gates.append({'clause':clause,'eligible':bool(accepted),'reasons':sorted(set(reason))})
   if accepted:eligible.append({'mode':mode})
  indices=Counter();access=[]
  def observer(side,probe):
   i=indices[side,probe['mode']];indices[side,probe['mode']]+=1
   if i>=3:return Observation(infrastructure_error=True,error='recorded-repeat-budget-exhausted')
   r=ix[side,probe['mode'],i];access.append({'side':side,'mode':probe['mode'],'repeat':i})
   return Observation(value=r['status']=='assertion-rejected',shape=(),dtype='bool')
  prop=Property(property_id='registered-source-rejection',clause_id='assertion-rejection-retention',oracle='outcome',precondition=lambda p:p in eligible,source=lambda p:observer('source',p))
  candidate=Candidate(candidate_id=sid,execute=lambda p:observer('target',p),origin='controlled-test; recorded-outcome-adapter',code_sha256=sha(target),target_binding='registered-target-operation')
  engine=certify(prop,candidate,eligible,budget=6,confirmations=2) if base and eligible else {'evidence_state':'undetermined','traces':[]}
  state=engine['evidence_state']
  verdict='violated' if state=='refuted' else 'preserved' if state=='supported-on-tested-inputs' and all(g['eligible'] for g in gates) else 'undetermined'
  result['predictions']['cosmit-core-recorded-test-outcome-adapter']=verdict
  result['predictions']['direct-llm']='not-run'
  predictions.append(result);audit.append({'sample_id':sid,'base_gate':bool(base),'assertions':assertions,'gates':gates,'engine':engine,'record_accesses':access})
 save(out/'predictions.json',predictions);save(out/'observer-audit.json',audit)
 save(out/'provenance.json',{'core_path':'src/cosmit/engine/certification.py','core_sha256':sha(ROOT/'src/cosmit/engine/certification.py'),'adapter_sha256':sha(Path(__file__)),'record_hashes':consumed,'reference_labels_read_during_prediction':False,'new_framework_calls':0,'new_model_calls':0,'llm_configuration':{'env_file_present':(ROOT/'.env.njusehub').exists(),'endpoint_present':bool(os.environ.get('NJUSEHUB_BASE_URL')),'key_present':bool(os.environ.get('NJUSEHUB_API_KEY'))},'scope':'new adapter over existing recorded test runs; not original pipeline or end-to-end intent inference'})

def score(data,out):
 labels={r['sample_id']:r for r in read(data/'evaluation-reference-labels.json')}
 preds=read(out/'predictions.json');methods=list(preds[0]['predictions']);metrics={}
 assert len(labels)==len(preds)==9
 def rate(n,d):return n/d if d else None
 for method in methods:
  c=Counter();rows=[]
  for p in preds:
   sid=p['sample_id'];actual=labels[sid]['expected']=='assertion-loss';v=p['predictions'][method]
   bucket=('TP' if actual else 'FP') if v=='violated' else ('FN' if actual else 'TN') if v=='preserved' else v
   c[bucket]+=1;rows.append({'sample_id':sid,'reference':labels[sid]['expected'],'prediction':v,'bucket':bucket})
  n=c['TP']+c['TN']+c['FP']+c['FN']
  metrics[method]={'counts':dict(c),'coverage':rate(n,9),'accuracy_on_determined':rate(c['TP']+c['TN'],n),'precision':rate(c['TP'],c['TP']+c['FP']),'recall_on_determined':rate(c['TP'],c['TP']+c['FN']),'end_to_end_detection_rate':None if c['not-run']==9 else rate(c['TP'],6),'false_rejection_rate_on_determined':rate(c['FP'],c['FP']+c['TN']),'f1':None if n==0 else rate(2*c['TP'],2*c['TP']+c['FP']+c['FN']),'rows':rows}
 save(out/'metrics.json',{'positive_class':'controlled assertion loss','samples':9,'underlying_tests':3,'development_only':True,'metrics':metrics})
 print(json.dumps({k:{a:b for a,b in v.items() if a!='rows'} for k,v in metrics.items()},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['predict','score']);p.add_argument('data',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 (predict if a.action=='predict' else score)(a.data,a.output)
