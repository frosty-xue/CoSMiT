"""Download original artifacts only; no execution or test synthesis."""
from collect_published_test_materials import ROOT, OUT, fetch
import json, concurrent.futures, hashlib

index=json.loads((ROOT/'analysis/annotation-package-2026-10-11/candidate-index.json').read_text(encoding='utf-8'))
repos=json.loads((OUT/'repositories.json').read_text())
jobs={}
for c in index:
    url=c['counterpart_url'].replace('https://github.com/','https://raw.githubusercontent.com/').replace('/blob/','/')
    jobs[OUT/'candidates'/c['candidate_id']/'original-counterpart.json']=url
for r in repos:
    if 'error' in r: continue
    name=r['repo']; dest=OUT/name.replace('/','__')
    tree=json.loads((dest/'tree.json').read_text())
    for entry in tree['tree']:
        p=entry['path']
        if entry['type']!='blob': continue
        select=False
        if name=='maybeLee/DLLens':
            select=p.endswith('.py') or p.endswith('confirmed_bugs.csv') or p.startswith('data/working_dir/rq1/tensorscope/')
        elif name=='tensorscopepro/Tensorscope': select=p.startswith('src/')
        elif name=='library-testing/Muffin': select=p.endswith(('.py','.md'))
        elif name=='lin-tan/eagle': select=p.startswith('src/') and p.endswith(('.py','.md'))
        if select: jobs[dest/'snapshot'/p]=f'https://raw.githubusercontent.com/{name}/{r["commit"]}/{p}'

def work(item):
    path,url=item
    try:
        data=fetch(url,path)
        return {'path':str(path.relative_to(OUT)).replace('\\','/'),'url':url,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    except Exception as e: return {'path':str(path.relative_to(OUT)), 'url':url,'error':str(e)}

if __name__=='__main__':
    print('Downloading',len(jobs),'original files',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(work,jobs.items()))
    (OUT/'payload-manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({'files':len(results),'errors':[r for r in results if 'error' in r]},indent=2))
