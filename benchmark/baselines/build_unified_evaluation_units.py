"""Package 110 provenance-linked units, with constructed tests and source-test leads.

No gold inference, network calls, framework execution or obsolete dataset reads.
"""
import argparse, ast, hashlib, importlib.util, json, shutil, subprocess
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'datasets/expansion-2026-09-18'
BASE=EXP/'assertion-batch-2026-09-28'

def build(out):
 out.mkdir(parents=True,exist_ok=False)
 inputs={}
 def raw(p):
  b=p.read_bytes();inputs[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
 def read(p):return json.loads(raw(p))
 def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 def copy(p,rel):
  q=out/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw(p));return str(Path(rel).as_posix())
 inventory=read(ROOT/'artifacts/analysis/evidence-inventory-2026-10-09/inventory.json')
 obligations={r['case_id']:r for r in read(ROOT/'artifacts/analysis/retained-obligations-2026-10-10/obligations.json')}
 regs={r['case_id']:r for r in read(BASE/'retained/registration.json')}
 records=read(BASE/'retained-executions-v2.json')
 probes=read(EXP/'runs/2026-09-20-dynamic-v3/inputs.freeze.json')
 p=BASE/'verify_batch.py';raw(p);s=importlib.util.spec_from_file_location('unit_verify',p);mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod);verified=mod.verify_retained()
 source_meta=read(BASE/'source-provenance.json')
 for item in source_meta:
  assert hashlib.sha256(raw(BASE/item['file'])).hexdigest()==item['sha256']
  copy(BASE/item['file'],'shared/registered-'+item['file'])
 save(out/'shared/registered-upstream-provenance.json',source_meta)
 copy(BASE/'retained.py','shared/retained-runner.py')
 # Local framework files are discovery leads only, not assumed runtime-matched tests.
 candidates=[];frameworks=[]
 for framework in ['pytorch','tensorflow']:
  checkout=Path('F:/codes/python/frameworks')/framework
  commit=subprocess.run(['git','-C',str(checkout),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
  files=sorted(checkout.rglob('*.py'))
  frameworks.append({'framework':framework,'checkout':str(checkout),'commit':commit,'searched_python_files':len(files),'version_alignment':'not established against execution versions'})
  for f in files:
   content=raw(f).decode('utf8');tree=ast.parse(content)
   snap=copy(f,'shared/source-search/'+framework+'/'+f.relative_to(checkout).as_posix())
   for cl in tree.body:
    if not isinstance(cl,ast.ClassDef):continue
    for n in cl.body:
     if not isinstance(n,ast.FunctionDef):continue
     attrs=sorted({ast.unparse(x) for x in ast.walk(n) if isinstance(x,ast.Attribute)})
     asserts=[{'line':x.lineno,'expression':ast.unparse(x)} for x in ast.walk(n) if isinstance(x,ast.Assert) or isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr.startswith('assert')]
     helpers=sorted({x.func.attr for x in ast.walk(n) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and isinstance(x.func.value,ast.Name) and x.func.value.id=='self' and x.func.attr.startswith('_')})
     candidates.append({'framework':framework,'file':snap,'class':cl.name,'method':n.name,'start':n.lineno,'end':n.end_lineno,'attributes':attrs,'assertions':asserts,'helper_dependencies':helpers,'commit':commit})
 public={}
 for part in ['discovery','unseen']:
  for c in read(ROOT/f'research-data/2026-09-17/{part}/cases.json'):
   if c['id']!='D0028':public[c['id']]=c
 units=[];lead_rows=[]
 for entry in inventory:
  cid=entry['case_id'];unitdir=out/'units'/cid;unitdir.mkdir(parents=True)
  u={'unit_id':cid,'family':entry['family'],'cohort':entry['batch'],'provenance':entry['provenance'],
     'behavior':{'status':entry['behavior_evidence'],'scope':'recorded inputs and registered contract only'},
     'test':None,'source_test_leads':[],'reference_label':None,'formal_intent_accuracy_eligible':False,'missing':[]}
  for side,code in entry['source_target_code'].items():
   (unitdir/(side+'-operation.py')).write_text(code,encoding='utf8')
  u['operation_files']={s:f'units/{cid}/{s}-operation.py' for s in ['source','target']}
  if cid in public:
   c=public[cid];save(unitdir/'behavior-inputs.json',c['inputs']);save(unitdir/'behavior-contract.json',c['contract'])
   u['behavior'].update(inputs=f'units/{cid}/behavior-inputs.json',contract=f'units/{cid}/behavior-contract.json')
   api=c['source']['api'];leaf=api.split('.')[-1];framework=c['source']['framework']
   allowed=[api] if framework=='pytorch' else ['math_ops.'+leaf,'gen_math_ops.'+leaf,'nn_ops.'+leaf,'special_math_ops.'+leaf,'tf.'+leaf]
   leads=[r for r in candidates if r['framework']==framework and any(a in r['attributes'] for a in allowed) and (r['method'].startswith('test') or r['assertions'])]
   for r in leads:
    u['source_test_leads'].append({**{k:v for k,v in r.items() if k!='attributes'},'matched_symbols':[a for a in allowed if a in r['attributes']],'status':'syntactic lead; obligation, input-domain and helper closure not yet reviewed'})
   # A generic OpInfo helper is useful but does not establish registration of this API.
   generics=[{k:v for k,v in r.items() if k!='attributes'} for r in candidates if r['framework']==framework and r['method'] in ['_test_reference_numerics','_compareCpu'] and ('unary' in r['file'])]
   u['generic_helper_leads']=generics
   u['readiness']='behavior-only-with-source-test-leads' if leads else 'behavior-only-source-test-unresolved'
   u['missing']=['来源可追溯的迁移测试及断言','上游方法义务与当前输入域的语义匹配','上游快照与运行版本对齐','输入生成器及helper依赖闭合','独立限域参照标签']
   lead_rows.append({'unit_id':cid,'family':entry['family'],'source_api':api,'direct_lead_count':len(leads),'generic_helper_count':len(generics),'test_pair_established':False,'priority':entry['priority']})
  else:
   selected=[r for r in probes if r['case_id']==cid];save(unitdir/'behavior-inputs.json',selected)
   u['behavior']['inputs']=f'units/{cid}/behavior-inputs.json'
   reg=regs[cid]
   if reg['status']=='registered':
    obligation=obligations[cid]
    for side in ['source','target']:
     copy(BASE/f'retained/{cid}-{side}.py',f'units/{cid}/{side}-test.py')
    save(unitdir/'test-records.json',{'versions':records['versions'],'records':[r for r in records['records'] if r['case_id']==cid]})
    frozen=[r for r in selected if r['input_index'] in [0,16]] if int(cid[1:])<=16 else []
    save(unitdir/'test-input-scope.json',{'input_origin':'frozen indices 0,16 replace upstream generator' if frozen else 'inputs generated by retained method body and frozen runner','frozen_scenarios':frozen,'runner_seed':1729,'execution_environment':'CPU eager with value bridge','configuration':reg['parameters'],'only_first_operation_return_perturbed':True})
    u['test']={'origin':'newly constructed operation substitution; not historical migrated test','source_file':f'units/{cid}/source-test.py','target_file':f'units/{cid}/target-test.py','registration':reg,'upstream_snapshot':'shared/registered-'+reg['file'],'upstream_provenance':'shared/registered-upstream-provenance.json','input_scope':f'units/{cid}/test-input-scope.json','records':f'units/{cid}/test-records.json','runner':'shared/retained-runner.py','obligations':obligation['obligations'],'scope_gaps':obligation['scope_gaps'],'review_category':obligation['review_category'],'scenarios':obligation['scenarios'],'baseline_and_transparency_passed':obligation['baseline_and_transparency_passed']}
    u['readiness']='constructed-test-evidence-packaged'
    u['missing']=['独立限域参照标签','方法共同运行覆盖','原生类型/布局/别名等未覆盖义务不得默认为保持']
   else:
    u['readiness']='behavior-only-unresolved-aliasing';u['missing']=[reg['reason'],'可执行原/目标测试对','独立限域参照标签']
  save(unitdir/'unit.json',u);units.append(u)
 save(out/'units.json',units);save(out/'source-test-search.json',{'framework_snapshots':frameworks,'per_candidate':lead_rows,'method':'AST exact API attribute references; generic helper leads separate','limits':'local sparse checkouts only; not a full upstream repository search; no migration provenance inferred'})
 save(out/'cohorts.json',{'behavior_units':[u['unit_id'] for u in units],'constructed_test_units':[u['unit_id'] for u in units if u['test']],'formal_intent_accuracy_units':[],'aliasing_unresolved':['E017','E021','E023'],'controlled_pilot':'separate 9 variants over E018/E022/E030; never add to 110 candidate count'})
 summary={'units':len(units),'behavior_units':110,'constructed_test_pairs':sum(bool(u['test']) for u in units),'initial_candidates_with_direct_source_test_leads':sum(r['direct_lead_count']>0 for r in lead_rows),'initial_candidates_without_direct_source_test_leads':sum(r['direct_lead_count']==0 for r in lead_rows),'initial_historical_test_pairs_established':0,'formal_intent_accuracy_units':0,'readiness_counts':dict(Counter(u['readiness'] for u in units)),'new_framework_or_model_calls':0}
 assert len(units)==110 and summary['constructed_test_pairs']==27
 assert sum(len(read(out/u['test']['records'])['records']) for u in units if u['test'])==1290
 save(out/'summary.json',summary);save(out/'input-hashes.json',inputs)
 lines=['# 原始80个候选：补证检索清单','','“直接线索”只表示在本地上游快照发现对应API引用，不代表已找到该候选的原始迁移测试。','','| ID | 家族 | 源API | 直接上游方法线索数 | 通用helper线索数 | 测试对已建立 |','|---|---|---|---:|---:|---|']
 for r in lead_rows:lines.append(f"| {r['unit_id']} | {r['family']} | {r['source_api']} | {r['direct_lead_count']} | {r['generic_helper_count']} | 否 |")
 (out/'initial-80-gap-table.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 save(out/'SHA256.json',{str(p.relative_to(out).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()})
 print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);build(p.parse_args().output)
