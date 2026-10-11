"""Create a hash-verified snapshot of the approved experimental data and analyses.

Copies only: existing runtime paths remain valid. No model or framework execution.
The only dataset eligible for archival is expansion-2026-09-18.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research-data/2026-10-11'
ANALYSIS = ROOT / 'analysis'
entries = []
excluded = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def put(source, destination):
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    before = sha(source)
    shutil.copy2(source, destination)
    assert sha(destination) == before == sha(source), f'copy changed: {source}'
    entries.append({'source': source.relative_to(ROOT).as_posix(),
                    'destination': destination.relative_to(ROOT).as_posix(),
                    'sha256': before, 'bytes': destination.stat().st_size})


def tree(source, destination):
    for p in sorted(source.rglob('*')):
        if not p.is_file():
            continue
        if any(x in p.parts for x in ('.git', '__pycache__', '.pytest_cache')) or p.suffix == '.pyc':
            excluded.append(str(p.relative_to(ROOT)))
            continue
        if p.name.startswith('.env') or p.suffix in ('.key', '.pem', '.pfx'):
            raise ValueError('credential-like file encountered; review required')
        put(p, destination / p.relative_to(source))


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def main():
    if DATA.exists():
        raise FileExistsError('Archive already exists; never overwrite a frozen archive')
    DATA.mkdir(parents=True)
    # Preserve the complete approved dataset's audit trail, including superseded
    # runs. README explicitly identifies which runs may enter main statistics.
    tree(ROOT / 'datasets/expansion-2026-09-18', DATA / 'expansion-2026-09-18')
    campaign = ROOT / 'artifacts/baselines/expansion-campaign-2026-10-10'
    derived = {'combined-110-counts.json', 'combined-110-results.json', 'cost-current.json',
               'coverage-current.json', 'REPORT.md', 'STATUS.md', 'validation.json'}
    for p in sorted(campaign.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        rel = p.relative_to(campaign)
        if p.suffix in ('.log', '.ps1'):
            dest = ANALYSIS / 'operations/expansion-campaign-2026-10-10' / rel
        elif len(rel.parts) == 1 and p.name in derived:
            dest = ANALYSIS / 'results/expansion-campaign-2026-10-10' / rel
        else:
            dest = DATA / 'baseline-campaign' / rel
        put(p, dest)
    tree(ROOT / 'artifacts/baselines/deepseek-r1-smoke-2026-10-10', DATA / 'diagnostics/deepseek-r1-smoke-2026-10-10')
    tree(ROOT / 'artifacts/baselines/restored-dependencies-2026-10-10', DATA / 'frozen-dependencies')
    tree(ROOT / 'artifacts/analysis', ANALYSIS / 'results')
    # Complete source snapshot retains sibling modules/import dependencies.
    tree(ROOT / 'benchmark/baselines', ANALYSIS / 'code-snapshot/benchmark/baselines')
    pure_scripts = ['analyze_research_export.py', 'analyze_combined_export.py',
                    'build_evidence_inventory.py', 'build_priority_adjudication.py',
                    'audit_retained_obligations.py', 'build_unified_evaluation_units.py',
                    'evaluate_controlled_assertions.py', 'extend_pilot_existing_baselines.py']
    for name in pure_scripts:
        put(ROOT / 'benchmark/baselines' / name, ANALYSIS / 'scripts' / name)
    docs = ['research-remaining-tasks.md', 'paper-writing-status-2026-09-17.md',
            'full-experiment-status.md', 'experiment-setup-scope-2026-09-30.json',
            'experiment-rewrite-evidence-2026-10-09.json', 'experiment-procedure-2026-09-16.md',
            'experiment-comparison-readiness-2026-09-27.md', 'dataset-collection-2026-09-17.md',
            'approach-todo-evidence-2026-09-28.md', 'research-data-counterexample-audit-2026-09-18.md']
    for name in docs:
        put(ROOT / 'docs' / name, ANALYSIS / 'reference-docs' / name)
    # Relocated lock is a new convenience file; original lock is retained byte-for-byte.
    lock = json.loads((DATA / 'frozen-dependencies/sources.lock.json').read_text(encoding='utf8'))
    for item in lock['sources']:
        item['checkout'] = (DATA / 'frozen-dependencies/sources' / item['name']).relative_to(ROOT).as_posix()
    lock['relocation_note'] = 'Archive-relative checkout mapping; source hashes and original sources.lock.json preserved.'
    write(DATA / 'frozen-dependencies/sources.relocated.lock.json', lock)
    # Check for accidental copying of the configured secret without displaying it.
    keys = []
    env = ROOT / '.env.njusehub'
    if env.exists():
        for line in env.read_text(encoding='utf8').splitlines():
            if line.startswith('NJUSEHUB_API_KEY='):
                key = line.split('=', 1)[1].strip().strip('\"\'')
                if len(key) >= 8:
                    keys.append(key.encode())
    for entry in entries:
        if keys:
            raw = (ROOT / entry['destination']).read_bytes()
            assert not any(k in raw for k in keys), 'Configured secret found in copied material'
    write(ANALYSIS / 'organization-manifest-2026-10-11.json', {
        'created_at': datetime.now().astimezone().isoformat(), 'mode': 'verified-copy; original files retained',
        'old_primary_data': 'research-data/2026-09-17 (unchanged)',
        'approved_dataset_only': 'datasets/expansion-2026-09-18',
        'excluded_cache_files': excluded, 'files': entries})
    write(ANALYSIS / 'organization-validation-2026-10-11.json', {
        'copied_files': len(entries), 'copied_bytes': sum(r['bytes'] for r in entries),
        'source_destination_sha256_match': True, 'configured_secret_scan_passed': True,
        'original_files_removed': 0, 'new_model_calls': 0, 'new_framework_executions': 0})
    print(json.dumps({'copied_files': len(entries), 'megabytes': round(sum(r['bytes'] for r in entries)/1048576, 2)}, indent=2))


if __name__ == '__main__':
    main()
