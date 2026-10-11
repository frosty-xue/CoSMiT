"""Build non-blinded, evidence-backed scoped dossiers; no new framework campaign."""
import argparse
import ast
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'datasets/expansion-2026-09-18'
RUN=DATA/'runs/2026-09-20-dynamic-v3'
BATCH=DATA/'assertion-batch-2026-09-28'


def assert_shape_preserved(expected_shape, observed):
    """New specification-derived assertion, applied to saved observations only."""
    assert observed['status']=='ok', 'operation did not return normally'
    assert observed['shape']==expected_shape, (expected_shape,observed['shape'])


def build(out):
    hashes={}
    def raw(p):
        b=p.read_bytes();hashes[str(p.relative_to(ROOT))]=hashlib.sha256(b).hexdigest();return b
    def read(p):return json.loads(raw(p))
    def module(name,p):
        raw(p);s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
    dynamic=module('dynamic_verify',DATA/'tools/verify_execution.py').verify(RUN,DATA)
    av=module('assertion_verify',BATCH/'verify_batch.py')
    retained=av.verify_retained()
    observations={}
    specs={}
    for side in ['source','target']:
        for fw in ['pytorch','tensorflow']:
            d=read(RUN/f'{side}-{fw}.json')
            observations.update({(r['case_id'],r['input_index'],r['repeat'],side):r for r in d['records']})
            if side=='source':specs.update(d['source_specifications'])
    probes=read(RUN/'inputs.freeze.json')
    witnesses=read(RUN/'counterexamples.json')
    regs={r['case_id']:r for r in read(BATCH/'retained/registration.json')}
    cases={r['case_id']:r for r in read(DATA/'candidates.json')}
    retained_records=read(BATCH/'retained-executions-v2.json')['records']
    text=raw(BATCH/'upstream/tf_clip.py').decode('utf8')
    cl=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='ClipTest')
    search=[]
    for n in cl.body:
        if isinstance(n,ast.FunctionDef) and 'ClipByValue' in n.name:
            search.append({'method':n.name,'start':n.lineno,'end':n.end_lineno,'body':ast.get_source_segment(text,n)})
    dossiers=[]
    for cid in ['E020','E029','E030']:
        c=cases[cid];reg=regs[cid];ws=[w for w in witnesses if w['case_id']==cid]
        snippets={s:raw(DATA/c[s]['code_path']).decode('utf8') for s in ['source','target']}
        for side,t in snippets.items():assert hashlib.sha256(t.encode()).hexdigest()==c[side]['code_sha256']
        bodies={s:raw(BATCH/f'retained/{cid}-{s}.py').decode('utf8') for s in ['source','target']}
        for side,t in bodies.items():assert hashlib.sha256(t.encode()).hexdigest()==reg[side+'_hash']
        original=[r for r in retained_records if r['case_id']==cid and r['mode']=='original']
        assert len(ws)==16 and len(original)==6
        pair_records=[r for key,r in observations.items() if key[0]==cid and key[1] in {w['input_index'] for w in ws}]
        assert len(pair_records)==96
        spec_keys={'E020':['tf.transpose'],'E029':['torch.clip','torch.clamp'],'E030':['tf.clip_by_value']}[cid]
        d={'case_id':cid,'date':'2026-10-10','review_kind':'non-blinded specification/code/record triangulation',
           'source_specs':{k:specs[k] for k in spec_keys},'source_specs_origin':'runtime docstrings saved in source framework records',
           'counterpart_code':snippets,'retained_registration':reg,'retained_test_bodies':bodies,
           'witness_inputs':ws,'witness_main_records':pair_records,'retained_original_records':original,
           'retained_verification':next(r for r in retained['matrix'] if r['case_id']==cid),
           'scoped_behavior_decision':'violated-on-documented-witness-inputs',
           'independent_gold':False,'blind_review':False,'full_historical_test_intent_label':None,
           'count_as_new_discovery':False,'independent_evaluation_eligible':False,
           'constructed_test_baseline_decision':'target-operation-fails' if cid!='E030' else 'passes-on-registered-2x3-input',
           'assertion_removed':False,'freeze_scope':'freeze evidence snapshot only; not independent evaluation gold'}
        dossiers.append(d)
    # Exhaustively apply a NEW shape assertion to the existing E030 observations.
    # This is retrospective evidence replay, not a new migrated upstream test.
    replay=[]
    for p in probes:
        if p['case_id']!='E030':continue
        t=p['arguments']['t']['values']
        def shape(x):return [len(x)]+shape(x[0]) if isinstance(x,list) and x else []
        expected=shape(t)
        for rep in range(3):
            for side in ['source','target']:
                obs=observations['E030',p['input_index'],rep,side]
                try:assert_shape_preserved(expected,obs);status='passed'
                except AssertionError:status='assertion-rejected'
                replay.append({'input_index':p['input_index'],'repeat':rep,'side':side,'input_shape':expected,'output_shape':obs.get('shape'),'result':status})
    assert len(replay)==384
    counts={side:dict(collections.Counter(r['result'] for r in replay if r['side']==side)) for side in ['source','target']}
    assert counts=={'source':{'passed':192},'target':{'passed':144,'assertion-rejected':48}}
    rejected={r['input_index'] for r in replay if r['result']=='assertion-rejected'}
    assert rejected=={w['input_index'] for w in witnesses if w['case_id']=='E030'}
    out.mkdir(parents=True,exist_ok=False)
    def save(name,d):(out/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for d in dossiers:save(d['case_id']+'-dossier.json',d)
    save('E030-upstream-search.json',{'searched_file':str(BATCH/'upstream/tf_clip.py'),'methods':search,'scope':'local fixed snapshot only; no exhaustive upstream repository claim'})
    save('E030-constructed-assertion-replay.json',{'origin':'new specification-derived assertion after known witness; not upstream migrated test','new_framework_calls':0,'records':replay,'counts':counts,'distinct_rejected_inputs':len(rejected),'independent_evaluation_eligible':False})
    save('verification.json',{'dynamic':dynamic,'retained_counts':retained['counts'],'dossier_cases':3,'new_behavior_discoveries':0,'new_independent_gold_labels':0,'new_framework_calls':0,'E030_saved_observation_assertion_counts':counts})
    save('input-hashes.json',hashes)
    print(json.dumps({'dossiers':3,'new_gold':0,'new_framework_calls':0,'shape_assertion_counts':counts},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);build(p.parse_args().output)
