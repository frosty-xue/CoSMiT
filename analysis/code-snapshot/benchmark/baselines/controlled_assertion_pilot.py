"""Construct and validate a small, explicitly synthetic assertion-loss pilot."""
import argparse, ast, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'datasets/expansion-2026-09-18'
BASE=DATA/'assertion-batch-2026-09-28'
IDS=['E018','E022','E030']
VARIANTS=['preserved','delete-assertions','vacuous-assertions']
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Mutate(ast.NodeTransformer):
 def __init__(self,kind):self.kind=kind;self.changes=[]
 def visit_Expr(self,n):
  v=n.value
  if isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute) and v.func.attr.startswith('assert'):
   self.changes.append({'line':n.lineno,'original':ast.unparse(n)})
   return ast.copy_location(ast.Pass() if self.kind=='delete-assertions' else ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Name(id='self',ctx=ast.Load()),attr='assertTrue',ctx=ast.Load()),args=[ast.Constant(True)],keywords=[])),n)
  return self.generic_visit(n)

def prepare(out):
 out.mkdir(parents=True,exist_ok=False)
 regs=[r for r in read(BASE/'retained/registration.json') if r['case_id'] in IDS]
 runner=(BASE/'retained.py').read_text(encoding='utf8')
 old="path=ROOT/'retained'/(cid+('-source.py' if side=='source' and mode=='original' else '-target.py'))"
 new="path=ROOT/'retained'/(cid+('-source.py' if side=='source' and mode=='original' else '-source-observed.py' if side=='source' else '-target.py'))"
 assert runner.count(old)==1
 (out/'frozen-runner.py').write_text(runner.replace(old,new),encoding='utf8')
 jobs=[];labels=[];changes=[]
 for variant in VARIANTS:
  d=out/variant;(d/'retained').mkdir(parents=True);(d/'registered-tests').mkdir()
  save(d/'retained/registration.json',regs)
  for cid in IDS:
   for side in ['source','target']:
    source=BASE/f'retained/{cid}-{side}.py'
    assert sha(source)==next(r for r in regs if r['case_id']==cid)[side+'_hash']
    shutil.copyfile(source,d/f'retained/{cid}-{side}.py')
   shutil.copyfile(BASE/f'retained/{cid}-target.py',d/f'retained/{cid}-source-observed.py')
   (d/'registered-tests'/cid).mkdir()
   for side in ['source','target']:shutil.copyfile(BASE/f'registered-tests/{cid}/{side}-function.py',d/f'registered-tests/{cid}/{side}-function.py')
   target=d/f'retained/{cid}-target.py'
   if variant!='preserved':
    mut=Mutate(variant);tree=mut.visit(ast.parse(target.read_text(encoding='utf8')));assert mut.changes
    target.write_text(ast.unparse(ast.fix_missing_locations(tree))+'\n',encoding='utf8')
    changes.append({'sample_id':cid+'/'+variant,'changes':mut.changes})
   jobs.append({'sample_id':cid+'/'+variant,'case_id':cid,'source_body':str((d/f'retained/{cid}-source.py').relative_to(out)),'source_observed_body':str((d/f'retained/{cid}-source-observed.py').relative_to(out)),'target_body':str(target.relative_to(out)),'runner':'frozen-runner.py','scope':'registered method, CPU eager, value bridge, first-operation probes','obligations':['shape'] if cid=='E018' else ['value','shape']})
   labels.append({'sample_id':cid+'/'+variant,'expected':'preserved-in-declared-probe-scope' if variant=='preserved' else 'assertion-loss','origin':'controlled transformation; requires execution confirmation','independent_historical_gold':False})
 save(out/'method-inputs.json',jobs);save(out/'reference-labels.json',labels);save(out/'transformations.json',changes)
 save(out/'protocol.json',{'cases':IDS,'variants':VARIANTS,'repeats':3,'modes':['original','observe','reinject','wrong-shape','wrong-value'],'framework_calls_planned':270,'prior_results_seen':True,'use':'development pilot; not held-out evaluation','source_instrumented_body':'unmodified operation-substituted body, separate from mutated target','counterpart_changes':False,'real_historical_migrations':False})
 save(out/'frozen-SHA256.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})

def execute(out,variant):
 for rel,digest in read(out/'frozen-SHA256.json').items():assert sha(out/rel)==digest,rel
 target=out/variant/'executions.json';assert not target.exists()
 sys.path.insert(0,str(BASE/'dependencies'))
 spec=importlib.util.spec_from_file_location('controlled_retained',out/'frozen-runner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.ROOT=out/variant;m.DATA=DATA;m.execute(target)

def summarize(out):
 results=[];allrows={}
 for variant in VARIANTS:
  rows=read(out/variant/'executions.json')['records'];assert len(rows)==90
  ix={(r['case_id'],r['side'],r['mode'],r['repeat']):r for r in rows};assert len(ix)==90
  allrows[variant]=ix
  for cid in IDS:
   modes=['original','observe','reinject','wrong-shape','wrong-value']
   for side in ['source','target']:
    for mode in modes:
     group=[ix[cid,side,mode,i] for i in range(3)]
     signatures=[{k:r[k] for k in ['status','phase','operation_count','first_observation','error']} for r in group]
     assert signatures[1:]==signatures[:1]*2,(cid,side,mode)
   baseline=all(ix[cid,s,m,i]['status']=='passed' for s in ['source','target'] for m in modes[:3] for i in range(3))
   assert baseline,(cid,variant,'baseline')
   probes=[]
   for mode in modes[3:]:
    s=ix[cid,'source',mode,0];t=ix[cid,'target',mode,0]
    assert s['first_observation']==t['first_observation'],(cid,variant,'different delivered observations')
    assert s['status'] in ['passed','assertion-rejected'] and t['status'] in ['passed','assertion-rejected']
    probes.append({'mode':mode,'source':s['status'],'target':t['status'],'lost_rejection':s['status']=='assertion-rejected' and t['status']=='passed'})
   expected=next(x['expected'] for x in read(out/'reference-labels.json') if x['sample_id']==cid+'/'+variant)
   loss=any(p['lost_rejection'] for p in probes)
   assert loss==(variant!='preserved'),(cid,variant,'expected label not confirmed')
   for side in ['source','target']:
    assert ix[cid,side,'observe',0]['first_observation']==ix[cid,side,'reinject',0]['first_observation']
   results.append({'sample_id':cid+'/'+variant,'baseline_passed':baseline,'probes':probes,'expected_label':expected,'expected_label_confirmed_in_scope':True,'evidence_label':'assertion-loss' if loss else 'preserved-in-declared-probe-scope'})
 # Catch accidental mutation of the source observer, a risk in reusing the old runner.
 for variant in VARIANTS[1:]:
  for key,r in allrows['preserved'].items():
   if key[1]=='source':assert {k:r[k] for k in ['status','operation_count','first_observation','error']}=={k:allrows[variant][key][k] for k in ['status','operation_count','first_observation','error']}
 save(out/'validation-results.json',results)
 save(out/'summary.json',{'samples':9,'base_candidates':3,'preserved_controls':3,'confirmed_assertion_loss_variants':6,'single_executions':270,'all_normal_baselines_passed':True,'source_observations_stable_across_variants':True,'new_real_counterpart_bugs':0,'method_accuracy_evaluated':False,'held_out':False})
 print(json.dumps(read(out/'summary.json'),indent=2))

def packet(out):
 """Export neutral identifiers and no expected labels in method-facing inputs."""
 import random
 items=read(out/'method-inputs.json');random.Random(20261010).shuffle(items)
 root=out/'evaluation-inputs';root.mkdir(exist_ok=False)
 public=[];answers=[]
 labels={r['sample_id']:r for r in read(out/'reference-labels.json')}
 for i,item in enumerate(items,1):
  sid=f'S{i:03d}';d=root/sid;d.mkdir()
  for field,name in [('source_body','source-test.py'),('source_observed_body','source-observed.py'),('target_body','target-test.py')]:shutil.copyfile(out/item[field],d/name)
  variant=item['sample_id'].split('/')[1]
  for side in ['source','target']:shutil.copyfile(out/variant/'registered-tests'/item['case_id']/(side+'-function.py'),d/(side+'-operation.py'))
  reg=next(r for r in read(BASE/'retained/registration.json') if r['case_id']==item['case_id'])
  public.append({'sample_id':sid,'entry':reg['entry'],'source_framework':'tensorflow','target_framework':'pytorch',
                 'obligations':item['obligations'],'scope':item['scope'],'files':{p.name:str(p.relative_to(root)) for p in d.iterdir()}})
  answers.append({'sample_id':sid,'internal_id':item['sample_id'],'expected':labels[item['sample_id']]['expected'],'role':'development-only; not held-out gold'})
 save(root/'samples.json',public);save(out/'evaluation-reference-labels.json',answers)
 save(root/'SHA256.json',{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','summarize','packet']);p.add_argument('output',type=Path);p.add_argument('--variant',choices=VARIANTS);a=p.parse_args()
 if a.action=='prepare':prepare(a.output)
 elif a.action=='execute':execute(a.output,a.variant)
 elif a.action=='summarize':summarize(a.output)
 else:packet(a.output)
