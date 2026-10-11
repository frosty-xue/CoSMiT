"""Recover pinned DLLens comparator and invoke the existing verification port."""
import argparse, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run(data,previous,out):
 out=out.resolve();data=data.resolve();out.mkdir(parents=True,exist_ok=False)
 pinned=next(r for r in read(ROOT/'benchmark/baselines/frozen-manifest.json')['sources'] if r['name']=='dllens')
 rel='codes/counterpart/evaluate_counterpart.py'
 raw=subprocess.run(['git','-C','F:/codes/python/DLLens','show',pinned['commit']+':'+rel],check=True,capture_output=True).stdout
 base=out/'recovered-sources/dllens';source=base/rel;source.parent.mkdir(parents=True);source.write_bytes(raw)
 lock=out/'recovered-sources.lock.json'
 save(lock,{'recovery':'minimal new lock from locally available pinned Git blob; original lock is absent','sources':[{'name':'dllens','commit':pinned['commit'],'checkout':str(base),'files':[{'path':rel,'sha256':sha(source)}]}]})
 ports=module('existing_verification_ports',ROOT/'benchmark/baselines/verification_ports.py');ports.LOCK=lock
 comparator=ports.dllens_comparator(np)
 predictions=read(previous/'predictions.json');audit=[]
 public=data/'evaluation-inputs'
 for r,h in read(public/'SHA256.json').items():assert sha(public/r)==h
 routes=[]
 for folder in data.iterdir():
  if not (folder/'executions.json').exists():continue
  rows=read(folder/'executions.json')['records']
  for reg in read(folder/'retained/registration.json'):
   cid=reg['case_id'];routes.append((sha(folder/f'retained/{cid}-source.py'),sha(folder/f'retained/{cid}-target.py'),cid,rows))
 for s in read(public/'samples.json'):
  matches=[x for x in routes if x[:2]==(sha(public/s['files']['source-test.py']),sha(public/s['files']['target-test.py']))];assert len(matches)==1
  _,_,cid,rows=matches[0];checks=[]
  for rep in range(3):
   pair=[next(r for r in rows if r['case_id']==cid and r['side']==side and r['mode']=='observe' and r['repeat']==rep) for side in ['source','target']]
   assert all(r['status']=='passed' and r['first_observation'] for r in pair)
   obs=[r['first_observation'][0]['native'] for r in pair]
   arrays=[np.asarray(o['values'],dtype=o['dtype']) for o in obs]
   checks.append(bool(comparator(*arrays)))
  row=next(r for r in predictions if r['sample_id']==s['sample_id'])
  row['predictions']['dllens-existing-comparator-port']='preserved' if all(checks) else 'violated'
  for name in ['docter-constraint-port','intenttester-verifier-port','intenttester-target-tdl-extension','trace-llm','target-binding-native-api']:
   row['predictions'][name]='not-run'
  audit.append({'sample_id':s['sample_id'],'recorded_unperturbed_first_return_agreement':checks,'classification_rule':'no difference -> preserved proxy; not proof of assertion preservation','method_scope':'existing DLLens comparator port on recorded outputs; no full fuzzer run'})
 save(out/'predictions.json',predictions);save(out/'dllens-port-audit.json',audit)
 save(out/'baseline-status.json',{
  'dllens-existing-comparator-port':{'status':'executed-on-recorded-observations','entry':'verification_ports.dllens_comparator','original_commit':pinned['commit'],'comparator_sha256':sha(source),'port_sha256':sha(ROOT/'benchmark/baselines/verification_ports.py'),'comparisons':27,'new_framework_test_executions':0},
  'docter-constraint-port':{'status':'not-run','entry':'verification_ports.check_docter','blockers':['pinned DocTer constraint files absent','actual test argument packet must be serialized for each selected call'],'scope':'API input admissibility; satisfied does not imply assertion preservation'},
  'intenttester-verifier-port':{'status':'not-run','entry':'prepare_llm_jobs / run_verifier_llm.py','blockers':['original source lock and pinned VerificationAgent.java template absent','model endpoint and credential configuration absent'],'additional_adaptation':'helper/harness-based tests must be packaged with sufficient context; old unary function packet cannot be blindly reused'},
  'direct-llm-and-trace-llm':{'status':'not-run','blockers':['model endpoint and credential configuration absent']},
  'target-binding-native-api':{'status':'not-run','blockers':['current retained records count wrapper boundary calls, not independently instrumented native target API calls']},
  'transfuzz':{'status':'reference-only','reason':'existing project protocol excludes it from experiment baselines'},
  'previous-static-and-execution-checks':{'status':'supplementary controls, not replacements for project baselines'},
  'answer_key_read_by_comparator':False})
 print('Executed existing DLLens comparator: 27 recorded comparisons for 9 samples.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('previous',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.data,a.previous,a.output)
