"""Fetch fixed-version public tests/support files, never execute them."""
import json, concurrent.futures, hashlib
from collect_published_test_materials import ROOT, OUT, fetch
ivy=OUT/'ivy-llc__ivy'
sha=json.loads((ivy/'commit.json').read_text())['sha']
tree=json.loads((ivy/'tree.json').read_text())['tree']
jobs=[]
for e in tree:
    p=e['path']
    if e['type']=='blob' and (p.startswith('ivy_tests/test_ivy/helpers/') or p in ['ivy_tests/conftest.py','ivy_tests/test_ivy/conftest.py','ivy_tests/test_ivy/test_frontends/conftest.py','ivy_tests/test_ivy/test_frontends/test_torch/__init__.py','ivy_tests/test_ivy/test_frontends/test_tensorflow/__init__.py','ivy/functional/frontends/tensorflow/__init__.py','ivy/functional/frontends/torch/__init__.py']):
        jobs.append((f'https://raw.githubusercontent.com/ivy-llc/ivy/{sha}/{p}',ivy/'snapshot'/p))
tfref=json.loads(fetch('https://api.github.com/repos/tensorflow/tensorflow/commits/v2.16.1',OUT/'tensorflow-tests/commit.json'))['sha']
for p in ['tensorflow/python/kernel_tests/math_ops/cwise_ops_unary_test.py','tensorflow/python/ops/math_ops.py','tensorflow/python/ops/array_ops.py','LICENSE']:
    jobs.append((f'https://raw.githubusercontent.com/tensorflow/tensorflow/{tfref}/{p}',OUT/'tensorflow-tests/snapshot'/p))
def run(job):
    url,path=job
    try:
        data=fetch(url,path)
        return {'url':url,'path':path.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(data).hexdigest()}
    except Exception as ex:return {'url':url,'error':str(ex)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:result=list(pool.map(run,jobs))
(OUT/'additional-test-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'files':len(result),'errors':[r for r in result if 'error'in r]},indent=2))
