"""Package existing public tests by API. No newly written or migrated tests."""
import ast, collections, hashlib, json, shutil, textwrap, zipfile
from pathlib import Path
from collect_published_test_materials import ROOT, OUT

DEST=ROOT/'research-data/2026-10-16/public-tests-110'
REPORT=ROOT/'analysis/results/public-tests-110-2026-10-16'
DEST.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
ivy=OUT/'ivy-llc__ivy'; sha=json.loads((ivy/'commit.json').read_text())['sha']
records=collections.defaultdict(list)

def norm(s):return s.replace('ivy.functional.frontends.','').replace('tensorflow.','tf.')
def record(file,node,repo,commit,rel,kind):
    start=min([node.lineno]+[d.lineno for d in node.decorator_list])
    return {'repository':repo,'commit':commit,'upstream_path':rel,'function':node.name,'line':start,'end_line':node.end_lineno,
            'url':f'https://github.com/{repo}/blob/{commit}/{rel}#L{start}','kind':kind,'local':str(file)}

for file in sorted((ivy/'snapshot/ivy_tests/test_ivy/test_frontends').rglob('*.py')):
    tree=ast.parse(file.read_text(encoding='utf-8')); constants={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant):
            for t in n.targets:
                if isinstance(t,ast.Name):constants[t.id]=n.value.value
    for n in ast.walk(tree):
        if not isinstance(n,ast.FunctionDef):continue
        apis=[]
        for d in n.decorator_list:
            if not isinstance(d,ast.Call):continue
            kwargs={k.arg:k.value for k in d.keywords}
            def value(key):
                x=kwargs.get(key)
                if isinstance(x,ast.Constant):return x.value
                if isinstance(x,ast.Name):return constants.get(x.id)
            fn=value('fn_tree')
            if isinstance(fn,str):apis.append(norm(fn))
            alias=kwargs.get('aliases')
            if isinstance(alias,(ast.List,ast.Tuple)):
                apis.extend(norm(a.value) for a in alias.elts if isinstance(a,ast.Constant) and isinstance(a.value,str))
            cls=value('class_tree');method=value('method_name')
            if isinstance(cls,str) and isinstance(method,str):apis.append(norm(cls)+'.'+method)
        for api in apis:
            records[api].append(record(file,n,'ivy-llc/ivy',sha,file.relative_to(ivy/'snapshot').as_posix(),'Ivy public frontend test'))

# Official existing tests fill sign and reverse-division gaps.
native=[('tensorflow-tests','tensorflow/tensorflow','tensorflow/python/kernel_tests/math_ops/cwise_ops_unary_test.py','testFloatBasic',['tf.sign','tf.math.sign']),
        ('tensorflow-tests','tensorflow/tensorflow','tensorflow/python/kernel_tests/array_ops/cast_op_test.py','testBasic',['tf.cast']),
        ('pytorch-tests','pytorch/pytorch','test/test_binary_ufuncs.py','test_rdiv',['torch.Tensor.__rtruediv__']),
        ('pytorch-tests','pytorch/pytorch','test/test_sparse.py','test_to_sparse',['torch.Tensor.to_sparse'])]
for folder,repo,rel,fn,apis in native:
    base=OUT/folder;commit=json.loads((base/'commit.json').read_text())['sha'];file=base/'snapshot'/rel
    node=next(n for n in ast.walk(ast.parse(file.read_text(encoding='utf-8'))) if isinstance(n,ast.FunctionDef) and n.name==fn)
    for api in apis:records[api].append(record(file,node,repo,commit,rel,'Official framework test'))

def lookup(api):
    if api in records:return records[api][0], 'exact API / explicit decorator alias'
    if api=='torch.neg' and 'torch.negative' in records:
        return records['torch.negative'][0], 'documented alias: https://docs.pytorch.org/docs/2.9/generated/torch.negative.html'
    if api.startswith('tf.') and api.count('.')==1:
        name=api[3:]
        # Ivy explicitly re-exports .math import * and .linalg.matmul.
        for other in ['tf.math.'+name]+(['tf.linalg.matmul'] if name=='matmul' else []):
            if other in records:return records[other][0], 'namespace re-export: Ivy tensorflow/__init__.py; selected '+other
    return None,None

def target_apis(c):
    code=(OUT/'candidates'/c['candidate_id']/'original-target-operation.py').read_text(encoding='utf-8')
    apis=[]
    for node in ast.walk(ast.parse(code)):
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div) and isinstance(node.left,ast.Constant) and c['target']['framework']=='pytorch':
            api='torch.Tensor.__rtruediv__'
            if api not in apis:apis.append(api)
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
        name=ast.unparse(node.func)
        if '(' not in name and name.startswith(('tf.','torch.')):api=name
        elif c['target']['framework']=='pytorch':api='torch.Tensor.'+node.func.attr
        else:continue
        if api not in apis:apis.append(api)
    return apis

def materialize(rec,folder,name):
    if not rec:return None
    original=Path(rec['local']);data=original.read_bytes()
    full=folder/(name+'-test-full.py');full.write_bytes(data)
    lines=data.decode('utf-8').splitlines(keepends=True)
    excerpt=textwrap.dedent(''.join(lines[rec['line']-1:rec['end_line']]))
    part=folder/(name+'-test-excerpt.py');part.write_text(excerpt,encoding='utf-8')
    result={k:v for k,v in rec.items() if k!='local'}
    result.update({'full_file':full.relative_to(DEST).as_posix(),'excerpt_file':part.relative_to(DEST).as_posix(),
                   'original_sha256':hashlib.sha256(data).hexdigest(),'excerpt_sha256':hashlib.sha256(part.read_bytes()).hexdigest()})
    return result

index=json.loads((ROOT/'analysis/annotation-package-2026-10-11/candidate-index.json').read_text(encoding='utf-8'))
rows=[]
for c in index:
    folder=DEST/'candidates'/c['candidate_id'];folder.mkdir(parents=True,exist_ok=True)
    for role in ['source','target']:
        shutil.copy2(OUT/'candidates'/c['candidate_id']/f'original-{role}-operation.py',folder/f'{role}-operation.py')
    rec,match=lookup(c['source_api']);source=materialize(rec,folder,'source')
    targets=[]
    for i,api in enumerate(target_apis(c),1):
        rec,how=lookup(api)
        targets.append({'api':api,'match':how,'test':materialize(rec,folder,f'target-{i:02}')})
    found=sum(t['test'] is not None for t in targets)
    status=('两端API测试齐' if source and found==len(targets) and targets else
            '源端有，目标部分有' if source and found else '仅源端有' if source else '仅目标端有' if found else '两端缺')
    notes=[]
    if len(targets)>1:notes.append('目标为组合：各API测试已分别收集，整段组合测试仍空缺')
    if len(targets)>1 and status=='两端API测试齐':status='两端组件测试齐，组合测试缺'
    if c['candidate_id']=='D0012':notes.append('保留真实配对 expm1→exp；不能因名称不一致改成 expm1→expm1')
    if c['candidate_id']=='D0050':notes.append('目标官方test_rdiv通过30/x测试反向除法；不是与源侧完全相同的1/x输入')
    if c['candidate_id']=='E012':notes.append('所选torch.min测试同时包含单输入归约与双输入逐元素分支，配对时用后者')
    if c['candidate_id']=='H010':notes.append('目标diagonal是trace组合的一部分；整段trace实现尚无现成测试')
    row={'candidate_id':c['candidate_id'],'source_api':c['source_api'],'target_calls':c['target_calls'],
         'status':status,'source_match':match,'source_test':source,'target_tests':targets,
         'whole_counterpart_test_verified':False,'input_oracle_alignment':'not yet reviewed','execution':'not run',
         'origin':'paired existing public API tests; not a historical migration record','notes':notes}
    rows.append(row)
    (folder/'metadata.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    text=[f'# {c["candidate_id"]}: {c["source_api"]} → {c["target_calls"]}', '',f'状态：**{status}**。这是代码材料覆盖，不代表迁移正确或测试已运行。', '',
          '## 源测试','']
    if source:text +=[f'- [{source["function"]}](source-test-excerpt.py)；[完整原文件](source-test-full.py)',f'- [上游固定版本]({source["url"]})；匹配方式：{match}']
    else:text+=['暂无现成测试，留空。']
    text+=['','## 目标测试','']
    for i,t in enumerate(targets,1):
        if t['test']:text +=[f'- `{t["api"]}`：[测试摘录](target-{i:02}-test-excerpt.py)、[完整原文件](target-{i:02}-test-full.py)、[上游]({t["test"]["url"]})；{t["match"]}']
        else:text +=[f'- `{t["api"]}`：暂无现成测试，留空。']
    text+=['','## 使用范围','','- 完整原文件未修改；摘录仅便于阅读，不能脱离原仓库依赖直接运行。',
           '- Ivy 测试通过公共助手调用原生参考实现及 Ivy 前端/后端；不是直接测试当前 DLLens 包装函数。',
           '- 输入范围和检查目标尚待对齐；不要把两套测试已有默认当作意图保持。',
           '- 缺少整段 counterpart 的现成测试时，不把组件测试合并计作已有组合测试。']
    text+=['- '+n for n in notes]
    (folder/'README.md').write_text('\n'.join(text)+'\n',encoding='utf-8')

# Preserve test helpers, configs, original relative paths and license material.
for folder in ['ivy-llc__ivy','tensorflow-tests','pytorch-tests']:
    shutil.copytree(OUT/folder/'snapshot',DEST/'upstream'/folder,dirs_exist_ok=True)
    shutil.copy2(OUT/folder/'commit.json',DEST/'upstream'/folder/'commit.json')
counts=collections.Counter(r['status'] for r in rows)
summary={'total':len(rows),'status_counts':dict(counts),'source_available':sum(bool(r['source_test']) for r in rows),
         'target_all_component_apis_available':sum(bool(r['target_tests']) and all(t['test'] for t in r['target_tests']) for r in rows),
         'composite_target_ids':[r['candidate_id'] for r in rows if len(r['target_tests'])>1],
         'missing':[{ 'candidate_id':r['candidate_id'],'source_missing':not bool(r['source_test']),'target_missing':[t['api'] for t in r['target_tests'] if not t['test']]} for r in rows if not r['source_test'] or not r['target_tests'] or any(not t['test'] for t in r['target_tests'])],
         'run_count':0,'historical_migration_claim':False}
for dest in [DEST,REPORT]:
    (dest/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'coverage.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
table=['# 110组现成测试代码覆盖表','','统计单位是候选ID（不是独立测试数）；相同公开测试可能被多个候选复用。','',
       '“有”指已保存公开测试代码（含已说明的别名/命名空间或运算符入口），不是执行成功，也不代表整段包装函数已覆盖。组合目标单列；尚未检查输入/意图对齐。','',
       '|候选|源 API|目标 API/调用|源端|目标端|备注|','|---|---|---|---|---|---|']
for r in rows:
    actual_calls=', '.join(t['api'] for t in r['target_tests'])
    table.append(f'|[{r["candidate_id"]}](candidates/{r["candidate_id"]}/README.md)|`{r["source_api"]}`|`{actual_calls}`|'+('有' if r['source_test'] else '缺')+'|'+('都有（组件）' if len(r['target_tests'])>1 and all(t['test'] for t in r['target_tests']) else '有' if r['target_tests'] and all(t['test'] for t in r['target_tests']) else '部分/缺')+'|'+('; '.join(r['notes']) or '输入与检查目标待核对')+'|')
(DEST/'COVERAGE.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
(REPORT/'COVERAGE.md').write_text(('\n'.join(table)+'\n').replace('](candidates/','](../../../research-data/2026-10-16/public-tests-110/candidates/'),encoding='utf-8')
readme='''# 110组公开测试代码材料包

入口：[逐组表](COVERAGE.md)。每个 candidates/ID 有源侧完整原测试文件、目标侧各API完整原测试文件、便于阅读的摘录和固定版本出处。

|覆盖情况|组数|
|---|---:|
|源侧API已有测试|110|
|目标单个API/运算符已有测试|93|
|目标组合的各组件已有测试，但整段组合测试缺失|17|
|缺少API级测试材料的组|0|

source-operation.py / target-operation.py 保存本批原始操作函数，供对照。它们不计入测试数量。17组组合测试缺口详见 summary.json 的 composite_target_ids；没有为这些组合另写新测试。

这是按用户允许的宽松口径配对的公开API测试材料，不是自动生成的迁移，也不是历史迁移记录。未修改任何测试断言；未执行测试；没有增加准确率或意图保持标签。

Ivy 测试依赖 Ivy、Hypothesis、pytest 和对应框架；测试调用与检查常在公共助手中。upstream/ 保留下载的原始目录和助手，但不是完整可安装仓库。运行时须使用 metadata 中固定提交的完整仓库和适配环境；摘录仅用于阅读。

TensorFlow 官方 sign 测试选用 testFloatBasic，它同时测试多个一元操作，包含 sign 的具体输入和参考检查。PyTorch 反向除法测试选用官方 test_rdiv（30/x），详见 D0050。cast 与稀疏转换也使用官方测试。

TensorFlow 顶层API测试若缺失，采用 Ivy 显式从 math 或 linalg 导出的同名入口测试，逐条记在 source_match / target_tests.match；torch.neg 使用官方文档说明的 negative 别名。没有修改测试内部名称。

组合目标各子操作有测试不代表组合函数有测试。旧 110 组的运行结果没有改动；新配对测试需要输入/检查目标核对和重新运行，才能用于后续实验。
'''
(DEST/'README.md').write_text(readme,encoding='utf-8')
hashes={p.relative_to(DEST).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.rglob('*') if p.is_file() and p.name!='SHA256.json'}
(DEST/'SHA256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
with zipfile.ZipFile(str(DEST)+'.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in DEST.rglob('*'):
        if p.is_file():archive.write(p,p.relative_to(DEST.parent))
print(json.dumps(summary,ensure_ascii=False,indent=2))
