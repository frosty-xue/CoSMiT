"""Conservative static inventory: API occurrence is a lead, never a validated pair."""
import ast, json, hashlib, re, shutil
from pathlib import Path
from collect_published_test_materials import ROOT, OUT

DEST=ROOT/'analysis/results/published-test-coverage-2026-10-16'
DEST.mkdir(parents=True,exist_ok=True)
CP=ROOT/'research-data/2026-10-16/crossprobe-intake'
def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def calls(path):
    code=path.read_text(encoding='utf-8-sig')
    try: tree=ast.parse(code)
    except SyntaxError as e: return {'syntax':'error','line':e.lineno,'error':e.msg,'calls':[]}
    aliases={}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for a in node.names: aliases[a.asname or a.name.split('.')[0]]=a.name
        elif isinstance(node,ast.ImportFrom) and node.module:
            for a in node.names: aliases[a.asname or a.name]=node.module+'.'+a.name
    def name(n):
        if isinstance(n,ast.Name): return aliases.get(n.id,n.id)
        if isinstance(n,ast.Attribute): return name(n.value)+'.'+n.attr
        return '<expression>'
    return {'syntax':'ok','assert_count':sum(isinstance(n,ast.Assert) for n in ast.walk(tree)),
            'calls':sorted(set(name(n.func).replace('tensorflow.','tf.') for n in ast.walk(tree) if isinstance(n,ast.Call)))}

pairs=json.loads((CP/'pair-inventory.json').read_text())
for p in pairs:
    p['source']=p['source'].replace('\\','/');p['target']=p['target'].replace('\\','/')
    p['source_static']=calls(CP/'snapshot'/p['source']);p['target_static']=calls(CP/'snapshot'/p['target'])
for target in sorted((CP/'snapshot/pytorch').glob('pt-*-tf*.py')):
    match=re.match(r'(pt-\d+)-tf',target.name)
    source=target.with_name(match.group(1)+'.py')
    if source.exists():
        pairs.append({'source':source.relative_to(CP/'snapshot').as_posix(),'target':target.relative_to(CP/'snapshot').as_posix(),
                      'pairing':'same issue-number filename; lineage needs original issue verification',
                      'semantic_pair_verified':False,'source_static':calls(source),'target_static':calls(target)})
dump(DEST/'crossprobe-all-pair-leads.json',pairs)

index=json.loads((ROOT/'analysis/annotation-package-2026-10-11/candidate-index.json').read_text(encoding='utf-8'))
rows=[]
for c in index:
    cid=c['candidate_id']; base=OUT/'candidates'/cid
    original=json.loads((base/'original-counterpart.json').read_text())
    samples=original.get('sample_inputs',[])
    # Verbatim extraction only. No imports, calls, assertions or conversions added.
    for role in ['source','target']:
        code=original['counterparts'][c[role]['framework']]
        (base/f'original-{role}-operation.py').write_text(code,encoding='utf-8')
    dump(base/'original-source-inputs.json',samples)
    leads=[{'source':p['source'],'target':p['target'],'target_syntax':p['target_static']['syntax'],
            'pairing':p['pairing'],'status':'API occurrence only; focal intent and original counterpart identity not established'}
           for p in pairs if c['source_api'] in p['source_static']['calls']]
    r={'candidate_id':cid,'source_api':c['source_api'],'target_calls':c['target_calls'],
       'source_url':c['counterpart_url'],'published_input_snippets':len(samples),
       'published_operations':True,'authentic_complete_pair_verified':False,
       'crossprobe_api_occurrence_leads':leads,
       'missing':['original complete source test and its oracle','published complete migrated target test linked to that source','identity with the already evaluated counterpart; otherwise separate evaluation required'],
       'material_directory':str(base)}
    rows.append(r)
    lines=[f'# {cid}: {c["source_api"]}', '',f'原始出处：{c["counterpart_url"]}', '',
           f'已收集作者原始输入代码片段 {len(samples)} 条，以及两侧操作函数。提取文件内容来自 JSON，未补写测试、转换输入或添加断言。',
           '', '**尚未补齐完整历史迁移测试对。** original-*-operation.py 是操作函数；original-source-inputs.json 是源框架输入片段。它们不是两个完整测试文件。', '',
           '公共比较器位于 ../../maybeLee__DLLens/snapshot/codes/counterpart/evaluate_counterpart.py。比较器的存在不证明源测试的独立断言曾被迁移。', '',
           f'CrossProbe 源脚本 API 出现线索：{len(leads)}；仅用于继续核查，不能计入完整测试对覆盖率。']
    for lead in leads: lines.append(f'- {lead["source"]} → {lead["target"]}；目标静态语法：{lead["target_syntax"]}')
    (base/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
dump(DEST/'candidate-coverage.json',rows)
summary={'candidates':len(rows),'with_published_inputs':sum(r['published_input_snippets']>0 for r in rows),
         'published_input_snippets':sum(r['published_input_snippets'] for r in rows),
         'verified_complete_historical_pairs':0,'crossprobe_pair_leads':len(pairs),
         'crossprobe_target_syntax_errors':sum(p['target_static']['syntax']=='error' for p in pairs),
         'candidates_with_source_api_occurrence_leads':[r['candidate_id'] for r in rows if r['crossprobe_api_occurrence_leads']]}
dump(DEST/'summary.json',summary)
lines=['# 110 组原始迁移测试材料覆盖表','','“未核实”不等于不存在。API 出现只代表检索线索；未运行第三方脚本，未自行迁移测试。','',
       '|候选|源 API|作者原始输入片段|CrossProbe API 出现线索|完整历史迁移对|','|---|---|---:|---:|---|']
for r in rows:
    lines.append(f'|[{r["candidate_id"]}](../../../research-data/2026-10-16/published-test-intake/candidates/{r["candidate_id"]}/README.md)|`{r["source_api"]}`|{r["published_input_snippets"]}|{len(r["crossprobe_api_occurrence_leads"])}|未核实|')
(DEST/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
hashes={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256.json'}
dump(OUT/'SHA256.json',hashes)
print(json.dumps(summary,ensure_ascii=False,indent=2))
