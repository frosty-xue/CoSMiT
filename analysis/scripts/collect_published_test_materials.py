"""Read-only upstream intake. Never execute or synthesize downloaded tests."""
import json, urllib.request, hashlib, concurrent.futures
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research-data/2026-10-16/published-test-intake'
OUT.mkdir(parents=True, exist_ok=True)

def fetch(url, path):
    if path.exists():
        return path.read_bytes()
    req = urllib.request.Request(url, headers={'User-Agent': 'CoSMiT-research-intake'})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data

def repo(name):
    dest = OUT / name.replace('/', '__')
    info = json.loads(fetch('https://api.github.com/repos/' + name, dest/'repository.json'))
    commit = json.loads(fetch(f'https://api.github.com/repos/{name}/commits/{info["default_branch"]}', dest/'commit.json'))['sha']
    tree = json.loads(fetch(f'https://api.github.com/repos/{name}/git/trees/{commit}?recursive=1', dest/'tree.json'))
    files = [x['path'] for x in tree['tree'] if x['type']=='blob']
    for p in files:
        if '/' not in p and (p.lower().startswith('readme') or p.lower().startswith('license')):
            fetch(f'https://raw.githubusercontent.com/{name}/{commit}/{p}', dest/'snapshot'/p)
    return {'repo':name, 'commit':commit, 'files':len(files), 'truncated':tree.get('truncated',False)}

if __name__=='__main__':
    names=['transfuzz/transfuzz','transfuzz/transfuzzbak','maybeLee/DLLens','tensorscopepro/Tensorscope','lin-tan/eagle','ise-uiuc/FreeFuzz','library-testing/Muffin']
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(repo,n):n for n in names}
        for job in concurrent.futures.as_completed(jobs):
            try: result=job.result()
            except Exception as exc: result={'repo':jobs[job], 'error':str(exc)}
            results.append(result)
            print(json.dumps(result), flush=True)
    (OUT/'repositories.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
