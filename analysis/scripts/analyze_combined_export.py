"""Combine public and expansion descriptive evidence without inferring gold labels.

Imports only offline verification functions, preserving original verification files.
Usage: python benchmark/baselines/analyze_combined_export.py NEW_OUTPUT
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / 'datasets/expansion-2026-09-18'
OLD = ROOT / 'research-data/2026-09-17'
PREVIOUS = ROOT / 'artifacts/analysis/research-data-2026-10-09'


def main(out):
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def module(name, path):
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    prior = read(PREVIOUS / 'metrics.json')
    for rel, expected in read(PREVIOUS / 'input-hashes.json').items():
        assert hashlib.sha256((OLD / rel).read_bytes()).hexdigest() == expected, rel
    initial = [c for part in ['discovery', 'unseen'] for c in read(OLD / part / 'cases.json') if c['id'] != 'D0028']
    expansion = read(EXP / 'candidates.json')
    # Same upstream counterpart path is the provenance-level deduplication key.
    initial_paths = {c['upstream_path'] for c in initial}
    expansion_paths = {c['upstream_path'] for c in expansion}
    assert len(expansion_paths) == len(expansion) == 30
    assert not initial_paths & expansion_paths
    old_families = {c['group'] for c in initial}
    new_families = {c['family'] for c in expansion}
    run = EXP / 'runs/2026-09-20-dynamic-v3'
    dynamic = module('dynamic_verifier', EXP / 'tools/verify_execution.py').verify(run, EXP)
    assertion = module('assertion_verifier', EXP / 'assertion-batch-2026-09-28/verify_batch.py')
    diagnostic = assertion.verify_diagnostic()
    retained = assertion.verify_retained()
    cases = read(run / 'case-results.json')
    inputs = read(run / 'input-outcomes.json')
    summary = read(run / 'summary.json')
    assert summary['case_statuses'] == dict(collections.Counter(c['status'] for c in cases))
    outcomes = dict(collections.Counter(r['status'] for r in inputs))
    assert len(inputs) == dynamic['qualified_inputs'] == summary['qualified_inputs']
    for c in cases:
        assert c['outcomes'] == dict(collections.Counter(r['status'] for r in inputs if r['case_id'] == c['case_id']))
    base_pairs = sum(p['paired_executions'] for p in prior['executions'].values())
    base_inputs = sum(p['inputs'] for p in prior['executions'].values())
    counts = collections.Counter(c['status'] for c in cases)
    combined = {
        'candidates': len(initial) + len(expansion),
        'families': len(old_families | new_families),
        'designed_inputs': base_inputs + summary['source_inputs'],
        'source_qualified_inputs': base_inputs + summary['qualified_inputs'],
        'source_unqualified_inputs': summary['source_unqualified_inputs'],
        'paired_executions': base_pairs + summary['completed_pairs'],
        'main_source_executions': base_pairs + summary['main_source_executions'],
        'main_target_executions': base_pairs + summary['main_target_executions'],
        'candidate_statuses': {
            'supported_in_registered_scope': len(initial) + counts['supported-on-qualified-inputs'],
            'replayed_behavior_discrepancy': counts['discrepancy-replayed'],
            'binding_undetermined': counts['undetermined-binding'],
        },
        'witness_inputs': dynamic['witness_inputs'],
        'witness_pairs_including_repeats': dynamic['witness_inputs'] * 3,
        'full_intent_accuracy': None,
    }
    combined['main_single_executions'] = combined['main_source_executions'] + combined['main_target_executions']
    assert sum(combined['candidate_statuses'].values()) == combined['candidates']
    assert combined['designed_inputs'] == combined['source_qualified_inputs'] + combined['source_unqualified_inputs']
    matrix = []
    for c in initial:
        matrix.append({'case_id': c['id'], 'batch': 'initial', 'family': c['group'], 'upstream_path': c['upstream_path'], 'status': 'supported_in_registered_scope'})
    for c in cases:
        provenance = next(x for x in expansion if x['case_id'] == c['case_id'])
        matrix.append({**c, 'batch': 'expansion', 'upstream_path': provenance['upstream_path']})
    result = {
        'scope': {'excluded': ['D0028', 'historical controls', 'dynamic-v1/v2 trials', 'assertion pilot duplicate evidence'], 'independent_gold': False},
        'deduplication': {'key': 'upstream_path', 'cross_batch_overlap': sorted(initial_paths & expansion_paths), 'family_overlap': sorted(old_families & new_families), 'initial_families': sorted(old_families), 'expansion_families': sorted(new_families)},
        'combined': combined,
        'expansion': {'summary': summary, 'input_outcomes': outcomes, 'verification': dynamic},
        'assertion_evidence_same_30_candidates': {'diagnostic': diagnostic, 'retained': retained},
        'initial_model_evidence_unchanged': {k: prior[k] for k in ['availability', 'methods', 'primary_failure_types', 'cost', 'negative_judgments']},
        'limitations': ['Different NumPy versions and input domains: report batch-stratified results.', 'Expansion has no model calls; do not extend model denominators to 110.', 'Only DLLens dense numerical branch compared on expansion; exception pipeline not rerun.', 'Replay and assertion evidence reuse candidates; never add them to candidate counts.'],
    }
    # Record hashes of complete verifier-covered inputs and records without modifying them.
    for base, manifest in [(run, run/'SHA256.json'), (assertion.ROOT, assertion.ROOT/'manifest.json'), (assertion.ROOT/'run-01', assertion.ROOT/'run-01/SHA256.json')]:
        entries = read(manifest)
        entries = entries.get('files', entries)
        for rel in entries:
            path = base/rel
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for rel in ['retained-executions-v2.json', 'retained/registration.json']:
        path = assertion.ROOT/rel
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    out.mkdir(parents=True, exist_ok=False)
    for name, data in [('metrics.json', result), ('candidate-results.json', matrix), ('input-hashes.json', hashes)]:
        (out/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'combined': combined, 'family_overlap': result['deduplication']['family_overlap'], 'expansion_outcomes': outcomes, 'retained_counts': retained['counts']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    main(parser.parse_args().output)
