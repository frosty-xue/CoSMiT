"""Run existing CoSMiT core and pinned DLLens comparator on saved observations.

No framework execution and no new gold labels. Preserve core binding gates,
including errors that happen before any target call; do not silently bypass them.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
import numpy as np
import verification_ports as ports

sys.path.insert(0, str(ports.ROOT / 'src'))
from cosmit.engine.certification import Candidate, Observation, Property, evaluate


def read(p):
    return json.loads(p.read_text(encoding='utf8'))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def run(campaign, lock):
    ports.LOCK = lock.resolve()
    comparator = ports.dllens_comparator(np)
    run = ports.ROOT / 'datasets/expansion-2026-09-18/runs/2026-09-20-dynamic-v3'
    quals = {(r['case_id'], r['input_index']): r['qualified'] for r in read(run / 'source-qualification.json')}
    frozen = {(r['case_id'], r['input_index']): r for r in read(run / 'inputs.freeze.json')}
    historical = {r['case_id']: r for r in read(run / 'case-results.json')}
    all_rows, summaries = [], []

    def observe(raw):
        if raw['status'] == 'ok':
            return Observation(value=raw['value'], dtype=raw['dtype'], shape=tuple(raw['shape']))
        return Observation(error=raw.get('error', raw['status']), infrastructure_error=raw['status'] != 'error')

    for folder in sorted((campaign / 'prepared').iterdir()):
        c = read(folder / 'case.json')
        cid = c['id']
        trace = read(folder / 'observations.json')
        rows = []
        for r in trace['records']:
            i = r['input_index']
            row = {'case_id': cid, 'input_index': i, 'repeat': r['repeat'], 'source_qualified': quals[cid, i]}
            if not quals[cid, i]:
                row['state'] = 'source-unqualified'
                rows.append(row)
                continue
            src, dst = r['source'], r['target']
            tolerance = frozen[cid, i]['tolerance']
            binding = bool(dst.get('calls'))
            row['target_binding_observed'] = binding
            row['self_test'] = 'passed' if src['status'] == dst['status'] == 'ok' else 'failed'
            row['dllens_dense'] = None
            if src['status'] == dst['status'] == 'ok':
                row['dllens_dense'] = bool(comparator(np.asarray(src['value'], dtype=src['dtype']),
                                                     np.asarray(dst['value'], dtype=dst['dtype'])))
            row['clauses'] = []
            for clause in ('value', 'shape', 'dtype'):
                prop = Property(cid, clause, clause, lambda _: True, lambda _, s=src: observe(s),
                                tolerance['atol'], tolerance['rtol'])
                candidate = Candidate(cid, lambda _, d=dst: observe(d), 'recorded-expansion-operation',
                                      ports.digest(c['target']),
                                      'registered-target-operation' if binding else 'unverified')
                result = evaluate(prop, candidate, {'input_index': i})
                result.pop('seconds', None)
                row['clauses'].append(result)
            rows.append(row)
        qualified = [r for r in rows if r['source_qualified']]
        witnesses = []
        for i in sorted({r['input_index'] for r in qualified}):
            group = [r for r in qualified if r['input_index'] == i]
            assert len(group) == 3 and {r['repeat'] for r in group} == {0, 1, 2}
            signatures = [ports.digest([{k: t[k] for k in ('source', 'target', 'outcome', 'clause_id')}
                                        for t in r['clauses']]) for r in group]
            if len(set(signatures)) == 1 and any(t['outcome'] == 'violation' for t in group[0]['clauses']):
                witnesses.append(i)
        core = ('refuted' if witnesses else 'supported-on-tested-inputs'
                if qualified and all(t['outcome'] == 'pass' for r in qualified for t in r['clauses'])
                else 'undetermined')
        dense = ('difference-observed' if any(r['dllens_dense'] is False for r in qualified) else
                 'no-difference-on-tested-inputs' if qualified and all(r['dllens_dense'] is True for r in qualified)
                 else 'undetermined')
        summaries.append({'case_id': cid, 'cosmit-core-recorded-operation': core,
                          'stable_witness_inputs': witnesses, 'dllens-dense-port': dense,
                          'self-test': 'passed' if all(r['self_test'] == 'passed' for r in qualified) else 'failed',
                          'target-binding': 'observed' if all(r['target_binding_observed'] for r in qualified) else 'not-observed-on-all-inputs',
                          'source_qualified_inputs': len(qualified) // 3,
                          'historical_expansion_behavior_status': historical[cid]['status']})
        all_rows.extend(rows)
    save(campaign / 'local-verifier-input-results.json', all_rows)
    save(campaign / 'local-verifier-results.json', summaries)
    save(campaign / 'local-verifier-provenance.json', {
        'core_sha256': hashlib.sha256((ports.ROOT / 'src/cosmit/engine/certification.py').read_bytes()).hexdigest(),
        'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'new_framework_executions': 0, 'new_model_calls': 0, 'numpy_comparator_runtime': np.__version__,
        'source_lock': str(lock.resolve()), 'qualified_input_count': sum(r['source_qualified_inputs'] for r in summaries),
        'binding_policy': 'same as existing experiment_worker: at least one recorded target operation call',
        'scope': 'existing core evaluate over recorded operations; not end-to-end test-intent inference; DLLens dense comparator only',
        'limitation': 'core binding gate remains undetermined for pre-call target exceptions even when separately replayed behavior discrepancy is established'} )
    print(json.dumps({k: dict(Counter(r[k] for r in summaries)) for k in
                      ('cosmit-core-recorded-operation', 'dllens-dense-port', 'self-test', 'target-binding')}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign', type=Path)
    p.add_argument('--sources-lock', type=Path, required=True)
    a = p.parse_args()
    run(a.campaign, a.sources_lock)
