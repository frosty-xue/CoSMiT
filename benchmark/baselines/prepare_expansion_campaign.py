"""Freeze model jobs from approved expansion observations, without model calls.

Reuses the existing verifier prompts. Never includes expected outputs, reference
labels, qualification decisions, or other verifiers' decisions in model inputs.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml
import verification_ports as ports

ROOT = ports.ROOT
EXP = ROOT / 'datasets/expansion-2026-09-18'
RUN = EXP / 'runs/2026-09-20-dynamic-v3'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(out, lock):
    ports.LOCK = lock.resolve()
    out.mkdir(parents=True, exist_ok=False)
    candidates = read(EXP / 'candidates.json')
    inputs = read(RUN / 'inputs.freeze.json')
    design = read(EXP / 'input-design.json')
    protocol = read(RUN / 'protocol.freeze.json')
    assert hashlib.sha256((RUN / 'inputs.freeze.json').read_bytes()).hexdigest() == protocol['inputs_sha256']
    assert len(candidates) == 30 and len(inputs) == 1920
    documents = {(side, fw): read(RUN / f'{side}-{fw}.json')
                 for side in ('source', 'target') for fw in ('pytorch', 'tensorflow')}
    index = {(r['case_id'], r['input_index'], r['repeat'], side): r
             for (side, fw), doc in documents.items() for r in doc['records']}
    schemas = {Path(f['path']).stem: f['path'] for s in read(lock)['sources']
               if s['name'] == 'docter' for f in s['files']}
    # Explicit canonical names; matching spelling alone does not authorize remapping arguments.
    aliases = {'torch.clip': 'torch.clamp', 'torch.concat': 'torch.cat'}
    # TF math names are exported aliases; keep the selected schema name in every record.
    for api in ('add', 'subtract', 'multiply', 'maximum', 'minimum', 'pow', 'atan2'):
        aliases['tf.' + api] = 'tf.math.' + api
    manifest = []
    docter = []
    for c in candidates:
        cid = c['case_id']
        frozen = [r for r in inputs if r['case_id'] == cid]
        assert len(frozen) == 64
        case = {'id': cid}
        for side in ('source', 'target'):
            meta = c[side]
            raw = (EXP / meta['code_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == meta['code_sha256']
            case[side] = {k: meta[k] for k in ('framework', 'entry')}
            case[side]['code'] = raw.decode('utf-8')
        case['source']['api'] = c['source_api']
        case['inputs'] = [r['arguments'] for r in frozen]
        d = design[c['family']]
        case['contract'] = {
            'description': 'For source-valid inputs in the registered finite domain, preserve '
                           'the source operation value, operation-derived output shape and dtype. '
                           'The registered source reference is: ' + d['reference_design'] + '.',
            'clauses': d['clauses'], 'family': c['family'],
            'registered_domain': d['constraints'],
            'domain_clarification': protocol['domain_clarification'],
            'tolerances_by_input_index': {str(r['input_index']): r['tolerance'] for r in frozen},
            'scope': protocol['scope'],
        }
        # All 64 inputs and all repetitions retained; no outcome-based trace selection.
        records = []
        allowed = ('status', 'value', 'shape', 'dtype', 'error_type', 'error', 'message', 'calls')
        for inp in frozen:
            for repeat in range(3):
                row = {'input_index': inp['input_index'], 'repeat': repeat}
                for side in ('source', 'target'):
                    obs = index.get((cid, inp['input_index'], repeat, side))
                    row[side] = ({k: obs[k] for k in allowed if k in obs} if obs else
                                 {'status': 'not-executed'})
                records.append(row)
        trace = {'status': 'recorded', 'records': records, 'versions': {
            fw: documents[('source', fw)]['version'] for fw in ('pytorch', 'tensorflow')}}
        trace['versions']['numpy'] = documents[('source', 'pytorch')]['numpy']
        jobs = ports.prepare_llm_jobs(case, trace)
        save(out / 'prepared' / cid / 'case.json', case)
        save(out / 'prepared' / cid / 'observations.json', trace)
        save(out / 'prepared' / cid / 'llm-jobs.json', jobs)
        manifest.extend({k: j[k] for k in ('case_id', 'kind', 'job_id', 'prompt_sha256')} |
                        {'prompt_chars': len(j['prompt'])} for j in jobs)
        api = c['source_api']
        name = api if api in schemas else aliases.get(api)
        schema_path = schemas.get(name)
        results = ([ports.check_docter(yaml.safe_load(ports.upstream('docter', schema_path)), r['arguments'])
                    for r in frozen] if schema_path else
                   [{'state': 'undetermined', 'reason': 'no-frozen-source-api-schema'} for r in frozen])
        docter.append({'case_id': cid, 'source_api': api, 'schema_api': name,
                       'schema_path': schema_path, 'explicit_alias': name is not None and name != api,
                       'current_version_compatibility': 'not-established',
                       'counts': dict(Counter(r['state'] for r in results)), 'inputs': results})
    # Recover missing original per-input DocTer results, with original explicit mapping.
    for part in ('discovery', 'unseen'):
        for c in read(ROOT / f'research-data/2026-09-17/{part}/cases.json'):
            if c['id'] == 'D0028':
                continue
            path = c.get('docter_file')
            results = ([ports.check_docter(yaml.safe_load(ports.upstream('docter', path)), a) for a in c['inputs']]
                       if path else [{'state': 'undetermined', 'reason': 'no-frozen-source-api-schema'} for _ in c['inputs']])
            docter.append({'case_id': c['id'], 'source_api': c['source']['api'], 'schema_path': path,
                           'counts': dict(Counter(r['state'] for r in results)), 'inputs': results,
                           'current_version_compatibility': 'not-established'})
    assert len(docter) == 110 and len(manifest) == 150
    save(out / 'docter-110.json', docter)
    save(out / 'jobs-manifest.json', manifest)
    files = [EXP / 'candidates.json', EXP / 'input-design.json', RUN / 'protocol.freeze.json',
             RUN / 'inputs.freeze.json', lock, Path(__file__), Path(ports.__file__)]
    files += [RUN / f'{side}-{fw}.json' for side, fw in documents]
    save(out / 'preparation.json', {
        'cases': 30, 'jobs': 150, 'scope': 'operation-level registered contracts; not full test-assertion intent',
        'model_calls': 0, 'new_framework_executions': 0, 'source_lock': str(lock.resolve()),
        'input_hashes': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'prompt_policy': 'existing prepare_llm_jobs, complete inputs and three repetitions; no verifier verdicts',
        'docter_scope': 'published historical literal constraint port; satisfaction is not intent preservation',
    })
    print(json.dumps({'cases': 30, 'jobs': 150, 'max_prompt_chars': max(j['prompt_chars'] for j in manifest),
                      'docter_candidates': len(docter)}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--sources-lock', type=Path, required=True)
    a = p.parse_args()
    prepare(a.output, a.sources_lock)
