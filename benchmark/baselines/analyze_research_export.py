"""Read-only descriptive analysis of the public export; no gold labels inferred.

Usage: python benchmark/baselines/analyze_research_export.py DATA NEW_OUTPUT
Excludes D0028 and historical controls; never reads obsolete datasets or raw archives.
"""
import argparse
import collections as co
import gzip
import hashlib
import json
import math
from pathlib import Path

KINDS = ['direct-llm', 'trace-llm', 'intenttester-source-tdl',
         'intenttester-target-api', 'intenttester-target-tdl-extension']


def count(xs):
    return dict(co.Counter(xs))


def rate(n, d):
    return {'numerator': n, 'denominator': d, 'percent': round(100*n/d, 4) if d else None}


def aggregate(values):
    # Same semantics as verification_ports.aggregate_checks; missing does not erase false.
    return 'rejected' if any(v is False for v in values) else 'accepted' if all(v is True for v in values) else 'undetermined'


def analyze(root, out):
    consumed = {}
    def read(rel):
        raw = (root/rel).read_bytes()
        consumed[rel] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    manifest = read('SHA256.json')
    integrity = []
    for rel, expected in manifest.items():
        raw = (root/rel).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        status = 'byte-match' if actual == expected else 'newline-normalized-match' if hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == expected else 'mismatch'
        integrity.append({'file': rel, 'status': status, 'expected': expected, 'actual': actual})
    assert not any(r['status'] == 'mismatch' for r in integrity), 'Unexplained manifest mismatch'
    cases, partitions, execution_metrics = {}, {}, {}
    for part in ['discovery', 'unseen']:
        cs = [c for c in read(f'{part}/cases.json') if c['id'] != 'D0028']
        for c in cs:
            assert c['id'] not in cases
            cases[c['id']] = c
            partitions[c['id']] = part
        rel = f'{part}/executions.jsonl.gz'
        raw = (root/rel).read_bytes(); consumed[rel] = hashlib.sha256(raw).hexdigest()
        rows = [json.loads(l) for l in gzip.decompress(raw).decode('utf8').splitlines() if l.strip()]
        rows = [r for r in rows if r['case_id'] in {c['id'] for c in cs}]
        expected = {(c['id'], i, j) for c in cs for i in range(len(c['inputs'])) for j in range(3)}
        assert len(rows) == len(expected) and {(r['case_id'], r['input_index'], r['repeat']) for r in rows} == expected
        groups = co.defaultdict(list)
        for r in rows:
            groups[(r['case_id'], r['input_index'])].append(r)
            for clause in r['clause_results']:
                for side in ['source', 'target']:
                    for key in ['value', 'shape', 'dtype']:
                        assert clause[side][key] == r[side][key]
        stable = 0
        for rs in groups.values():
            signatures = [json.dumps({side:{k:r[side].get(k) for k in ['status','value','shape','dtype','calls','error']} for side in ['source','target']}, sort_keys=True) for r in rs]
            stable += len(set(signatures)) == 1
        execution_metrics[part] = {
            'candidates':len(cs), 'families':len({c['group'] for c in cs}),
            'inputs':len(groups), 'paired_executions':len(rows),
            'source_reference_supported_pairs':sum(r['source_reference_supported'] for r in rows),
            'stable_inputs':rate(stable,len(groups)),
            'dllens_agreement_pairs':sum(r['dllens_agrees'] for r in rows),
            'clause_outcomes':count(v['outcome'] for r in rows for v in r['clause_results']),
            'versions':count(json.dumps(r['versions'],sort_keys=True) for r in rows),
            'direction_counts':count(c['source']['framework']+'->'+c['target']['framework'] for c in cs),
        }
    ids = set(cases)
    primary = [r for r in read('model-primary.json') if r['case_id'] in ids]
    retries = [r for r in read('model-retry.json') if r['case_id'] in ids]
    ix = {r['job_id']:r for r in primary}
    assert len(ix) == len(primary) == len(ids)*5
    assert {(r['case_id'],r['kind']) for r in primary} == {(c,k) for c in ids for k in KINDS}
    assert len({r['job_id'] for r in retries}) == len(retries)
    for r in retries:
        before = ix[r['job_id']]
        assert before['status'] == 'failed'
        assert all(r[k] == before[k] for k in ['case_id','kind','prompt_sha256'])
    merged = {**ix, **{r['job_id']:r for r in retries}}
    views = {'primary':{j:r['status'] for j,r in ix.items()}}
    for view in ['retry-view','format-sensitivity']:
        rows = [r for part in ['discovery','unseen'] for r in read(f'{part}/{view}.json') if r['case_id'] in ids]
        assert len(rows)==len(ix) and {r['job_id'] for r in rows}==set(ix)
        for r in rows: assert r['case_id']==ix[r['job_id']]['case_id']
        views[view] = {r['job_id']:r['status'] for r in rows}
    assert views['retry-view']=={j:r['status'] for j,r in merged.items()}
    availability = {}
    for view, statuses in views.items():
        availability[view] = {}
        for part in ['all','discovery','unseen']:
            selected = [r for r in primary if part=='all' or partitions[r['case_id']]==part]
            availability[view][part] = {k:rate(sum(statuses[r['job_id']]=='completed' for r in selected if k=='all' or r['kind']==k),sum(k=='all' or r['kind']==k for r in selected)) for k in ['all']+KINDS}
    matrix_views={}
    for view, records in [('primary',primary),('retry-view',list(merged.values()))]:
        by = {(r['case_id'],r['kind']):r for r in records}
        matrix=[]
        for cid,c in sorted(cases.items()):
            row={'case_id':cid,'partition':partitions[cid],'family':c['group'],**c['verdicts']}
            for k in ['direct-llm','trace-llm']:
                r=by[cid,k];row[k]=r['decision'].get('verdict','undetermined') if r['status']=='completed' else 'failed'
            checks=[]
            for k in KINDS[2:]:
                r=by[cid,k];checks.append(r['decision'].get('valid') if r['status']=='completed' else None)
            row['intenttester-verifier-port']=aggregate(checks[:2])
            row['intenttester-target-tdl-extension']=aggregate(checks)
            row['intenttester-complete-pair']=all(by[cid,k]['status']=='completed' for k in KINDS[2:4])
            matrix.append(row)
        matrix_views[view]=matrix
    methods = {}
    for view, matrix in matrix_views.items():
        methods[view]={part:{m:count(r[m] for r in matrix if part=='all' or r['partition']==part) for m in ['self-test','target-binding','dllens-port','cosmit-registered-clauses','direct-llm','trace-llm','intenttester-verifier-port','intenttester-target-tdl-extension']} for part in ['all','discovery','unseen']}
    failures={k:count(r.get('error_type') or 'unknown' for r in primary if r['kind']==k and r['status']!='completed') for k in KINDS}
    def costs(rows):
        complete=[r for r in rows if isinstance(r.get('usage'),dict) and all(isinstance(r['usage'].get(k),(float,int)) for k in ['prompt_tokens','completion_tokens','total_tokens'])]
        return {'physical_calls':len(rows),'complete_usage_calls':len(complete),'incomplete_usage_calls':len(rows)-len(complete),
                'reported_tokens':sum((r.get('usage') or {}).get('total_tokens') or 0 for r in rows),
                'reported_prompt_tokens':sum((r.get('usage') or {}).get('prompt_tokens') or 0 for r in rows),
                'reported_completion_tokens':sum((r.get('usage') or {}).get('completion_tokens') or 0 for r in rows),
                'recorded_request_seconds_not_latency_or_walltime':sum(r.get('seconds') or 0 for r in rows)}
    cost={v:costs(rs) for v,rs in [('primary',primary),('retries',retries),('physical_total',primary+retries)]}
    cost['primary_by_kind']={k:costs([r for r in primary if r['kind']==k]) for k in KINDS}
    negatives=[{'case_id':r['case_id'],'kind':r['kind'],'decision':r['decision']} for r in primary if r['status']=='completed' and (r['decision'].get('valid') is False or r['decision'].get('verdict') not in [None,'preserved','undetermined'])]
    family_rates={k:sum(sum(r['status']=='completed' for r in primary if r['kind']==k and cases[r['case_id']]['group']==f)/sum(r['kind']==k and cases[r['case_id']]['group']==f for r in primary) for f in {c['group'] for c in cases.values()})/len({c['group'] for c in cases.values()})*100 for k in KINDS}
    supplements={}
    def flat(v):
        return [x for a in v for x in flat(a)] if isinstance(v,list) else [v]
    def shape(v):
        return [len(v)]+shape(v[0]) if isinstance(v,list) and v else []
    for name in ['tf-tutorial','lstm','alexnet','vgg16']:
        d=read(f'supplements/{name}-observations.json');records=d['observations'];errors=[]
        for r in records:
            a=r.get('source_values',r.get('source'));b=r.get('target_values',r.get('target'))
            if isinstance(a,dict): a=a.get('values',a.get('value'))
            if isinstance(b,dict): b=b.get('values',b.get('value'))
            assert a is not None and b is not None
            assert shape(a)==shape(b)
            dif=max(abs(x-y) for x,y in zip(flat(a),flat(b)));assert math.isclose(dif,r['max_absolute_difference'],abs_tol=1e-15)
            assert all(math.isfinite(x) for x in flat(a)+flat(b));errors.append(dif)
        supplements[name]={'paired_observations':len(records),'max_absolute_difference':max(errors),'shape_and_finiteness_recomputed':True,'within_absolute_1e_6':all(e<=1e-6 for e in errors)}
    ts=read('supplements/tensorscope.json')['records']
    assert len({(r['input'],r['repeat']) for r in ts})==len(ts)
    assert all(all(r[k]==[abs(r['value'])] for k in ['source','onnx','torch']) for r in ts)
    supplements['tensorscope']={'triplets':len(ts),'distinct_input_ids':len({r['input'] for r in ts}),'recomputed_abs_agreement':True}
    supplements['besser_source']=read('supplements/besser-source.json')
    for k in ['results']:supplements['besser_source'].pop(k,None)
    result={'scope':{'data':str(root.resolve()),'included_partitions':['discovery','unseen'],'excluded_case_ids':['D0028'],'excluded_controls':True,'independent_gold':False},
            'integrity':count(r['status'] for r in integrity),'executions':execution_metrics,'availability':availability,'methods':methods,'primary_failure_types':failures,'cost':cost,'negative_judgments':negatives,'family_macro_availability_percent':family_rates,'supplements':supplements,
            'unavailable_metrics':{'precision_recall_f1_false_rejection':'No independent reference labels; finite agreement is not gold.','rq2_search_efficiency':'No common-candidate strategy campaigns or first stable witness sequence in this export.','rq3_diagnosis_conditions':'No independent cause/condition labels or discovery-validation condition results.','filtered_docter_counts':'No per-case constraint verdicts in cases.json; aggregate matrices cannot safely be filtered for D0028.','format_view_semantic_verdicts':'Format view contains statuses only; recovered decisions omitted.','monetary_cost_and_latency':'Missing billing/usage and request durations contaminated by pause and concurrency.'}}
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('metrics.json',result),('candidate-methods.json',matrix_views),('integrity.json',integrity),('input-hashes.json',consumed)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'executions':execution_metrics,'availability':availability,'methods':methods['primary']['all'],'cost':cost,'failures':failures,'negative_cases':len({r['case_id'] for r in negatives})},ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('output',type=Path);a=p.parse_args();analyze(a.data,a.output)
