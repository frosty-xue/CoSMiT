"""Recover pinned public verifier resources, without configuring/calling an LLM."""
import argparse, concurrent.futures, hashlib, json, subprocess, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'CoSMiT-baseline-recovery'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read()
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def restore(out):
 out.mkdir(parents=True,exist_ok=False)
 pins={r['name']:r for r in read(ROOT/'benchmark/baselines/frozen-manifest.json')['sources']}
 log=[];sources=[]
 for name in ['docter','intenttester']:
  pin=pins[name];repo=pin['remote'].removesuffix('.git').split('github.com/')[-1]
  try:
   tree=json.loads(get(f'https://api.github.com/repos/{repo}/git/trees/{pin["commit"]}?recursive=1'))
   assert not tree.get('truncated'), 'truncated upstream tree'
   save(out/(name+'-tree.json'),tree)
   if name=='docter':chosen=[x for x in tree['tree'] if x['path'].startswith('constraints_extracted/') and x['path'].endswith(('.yaml','.yml'))]
   else:chosen=[x for x in tree['tree'] if x['path']=='src/main/java/framework/VerificationAgent.java']
   assert chosen, 'required paths absent'
   # Only source-API schemas relevant to the approved 110 cases.
   if name=='docter':
    cases=[c for part in ['discovery','unseen'] for c in read(ROOT/f'research-data/2026-09-17/{part}/cases.json') if c['id']!='D0028']
    explicit={c.get('docter_file') for c in cases if c.get('docter_file')}
    expansion=read(ROOT/'datasets/expansion-2026-09-18/candidates.json')
    wanted={c['source']['api'] for c in cases}|{c['source_api'] for c in expansion}
    # Additional canonical aliases are retrieval leads, not automatic semantic mappings.
    names=wanted|{'tf.math.'+x[3:] for x in wanted if x.startswith('tf.') and x.count('.')==1}|{'torch.clamp','torch.cat'}
    chosen=[x for x in chosen if x['path'] in explicit or Path(x['path']).stem in names]
   checkout=out/'sources'/name
   def fetch(item):
    b=get(f'https://raw.githubusercontent.com/{repo}/{pin["commit"]}/{item["path"]}')
    assert gitsha(b)==item['sha'],item['path']
    p=checkout/item['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    return {'path':item['path'],'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':item['sha']}
   files=[];failures=[]
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    futures={pool.submit(fetch,x):x for x in chosen}
    for f in concurrent.futures.as_completed(futures):
     try:files.append(f.result())
     except Exception as e:failures.append({'path':futures[f]['path'],'error_type':type(e).__name__,'message':str(e)[:200]})
   sources.append({'name':name,'commit':pin['commit'],'checkout':str(checkout.resolve()),'files':sorted(files,key=lambda x:x['path'])})
   log.append({'name':name,'requested':len(chosen),'restored':len(files),'failures':failures})
  except Exception as e:log.append({'name':name,'status':'blocked','error_type':type(e).__name__,'message':str(e)[:200]})
 pin=pins['dllens'];rel='codes/counterpart/evaluate_counterpart.py'
 b=subprocess.run(['git','-C','F:/codes/python/DLLens','show',pin['commit']+':'+rel],check=True,capture_output=True).stdout
 checkout=out/'sources/dllens';p=checkout/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 sources.append({'name':'dllens','commit':pin['commit'],'checkout':str(checkout.resolve()),'files':[{'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':gitsha(b)}]})
 save(out/'sources.lock.json',{'recovery':'new partial lock for existing verifier ports; not original archived lock','sources':sources})
 save(out/'recovery.json',{'sources':log,'model_configuration':'intentionally blank per user; no requests sent'})
 print(json.dumps(log,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);restore(p.parse_args().output)
