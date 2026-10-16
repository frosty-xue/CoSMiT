"""Collect public tests and index explicit frontend API strings; no translation."""
import ast, json, concurrent.futures, hashlib
from collect_published_test_materials import ROOT, OUT, fetch

repo=OUT/'ivy-llc__ivy'
commit=json.loads((repo/'commit.json').read_text())['sha']
tree=json.loads((repo/'tree.json').read_text())
paths=[x['path'] for x in tree['tree'] if x['type']=='blob' and x['path'].endswith('.py') and (
    x['path'].startswith('ivy_tests/test_ivy/test_frontends/test_torch/') or
    x['path'].startswith('ivy_tests/test_ivy/test_frontends/test_tensorflow/') or
    x['path'] in ['ivy_tests/test_ivy/helpers/function_testing.py','ivy_tests/test_ivy/helpers/testing_helpers.py'])]
def get(p):
    url=f'https://raw.githubusercontent.com/ivy-llc/ivy/{commit}/{p}'
    try:
        data=fetch(url,repo/'snapshot'/p)
        return {'path':p,'url':url,'sha256':hashlib.sha256(data).hexdigest()}
    except Exception as e: return {'path':p,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: manifest=list(pool.map(get,paths))
(repo/'test-payload-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
records=[]
for item in manifest:
    if 'error' in item: continue
    code=(repo/'snapshot'/item['path']).read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(code)):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        strings=set()
        for dec in node.decorator_list:
            for n in ast.walk(dec):
                if isinstance(n,ast.Constant) and isinstance(n.value,str): strings.add(n.value.replace('tensorflow.','tf.'))
        if strings:records.append({'function':node.name,'line':node.lineno,'path':item['path'],'url':item['url'].replace('raw.githubusercontent.com/','github.com/').replace('/'+commit+'/', '/blob/'+commit+'/')+f'#L{node.lineno}','api_strings':sorted(strings)})
index=json.loads((ROOT/'analysis/annotation-package-2026-10-11/candidate-index.json').read_text(encoding='utf-8'))
coverage=[{'candidate_id':c['candidate_id'],'source_api':c['source_api'],'tests':[r for r in records if c['source_api'] in r['api_strings']], 'classification':'public frontend compatibility test; not a historical migrated test for the existing DLLens counterpart'} for c in index]
dest=ROOT/'analysis/results/published-test-coverage-2026-10-16'
(dest/'ivy-api-test-leads.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8')
print(json.dumps({'downloaded':len(manifest),'errors':[m for m in manifest if 'error'in m],'exact_api_coverage':sum(bool(c['tests']) for c in coverage),'missing':[c['candidate_id'] for c in coverage if not c['tests']]},indent=2))
