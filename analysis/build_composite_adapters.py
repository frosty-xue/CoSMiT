"""Package fixed public samples + unchanged counterpart functions + public oracle."""
import ast,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research-data/2026-10-16/composite-adapters-17'
PUBLIC=ROOT/'research-data/2026-10-16/public-tests-110'
RAW=ROOT/'research-data/2026-10-16/published-test-intake'
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 records=json.loads((PUBLIC/'coverage.json').read_text(encoding='utf-8'))
 index={c['candidate_id']:c for c in json.loads((ROOT/'analysis/annotation-package-2026-10-11/candidate-index.json').read_text(encoding='utf-8'))}
 oracle=RAW/'ivy-llc__ivy/snapshot/ivy_tests/test_ivy/helpers/assertions.py'
 text=oracle.read_text(encoding='utf-8');tree=ast.parse(text)
 selected=[]
 for n in tree.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOLERANCE_DICT' for t in n.targets):selected.append(ast.get_source_segment(text,n))
  if isinstance(n,ast.FunctionDef) and n.name in ['assert_all_close','assert_same_type_and_shape','value_test']:selected.append(ast.get_source_segment(text,n))
 # Functions unchanged; only NumPy imported. The ivy-dependent promotion branch is never used.
 (OUT/'public_oracle.py').write_text('# Verbatim selected functions from pinned Ivy assertions.py; only test_dtypes=True supported.\nimport numpy as np\n\n'+'\n\n'.join(selected)+'\n',encoding='utf-8')
 shutil.copy2(oracle,OUT/'original-ivy-assertions.py')
 cases=[]
 for r in records:
  if len(r['target_tests'])<=1:continue
  cid=r['candidate_id'];d=OUT/'cases'/cid;d.mkdir(parents=True,exist_ok=True)
  raw=RAW/'candidates'/cid/'original-counterpart.json';shutil.copy2(raw,d/'counterpart.json')
  c=json.loads(raw.read_text(encoding='utf-8'));meta=index[cid]
  for role in ['source','target']:(d/f'{role}-operation.py').write_text(c['counterparts'][meta[role]['framework']],encoding='utf-8')
  snippet=PUBLIC/r['source_test']['excerpt_file'];shutil.copy2(snippet,d/'public-source-test-excerpt.py')
  settings={'rtol':None,'atol':1e-6,'test_dtypes':True}
  for node in ast.walk(ast.parse(snippet.read_text(encoding='utf-8'))):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='test_frontend_function':
    for k in node.keywords:
     if k.arg in settings:settings[k.arg]=ast.literal_eval(k.value)
  assert settings['test_dtypes'] is True
  item={'candidate_id':cid,'source_framework':meta['source']['framework'],'target_framework':meta['target']['framework'],
        'sample_count':len(c['sample_inputs']),'sample_source':meta['counterpart_url'],'public_test_url':r['source_test']['url'],
        'oracle_settings':settings,'original_json_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
        'scope':'controlled fixed-public-sample adaptation; not original Ivy strategy replay; not independent intent evidence'}
  cases.append(item);dump(d/'adaptation.json',item)
  (d/'README.md').write_text(f'''# {cid} 完整函数受控适配

输入：counterpart.json 中 {len(c['sample_inputs'])} 条作者 sample_inputs，未补写新输入。两侧操作函数保持原文。

执行入口：在包根运行 `python run_adapters.py --case {cid} --output results/{cid}.json`。

适配：在源框架创建同一输入，将张量经 NumPy 按值和 dtype 转到目标框架；以源函数签名绑定参数，并调用完整目标函数。目标转换不保持共享存储、设备或梯度，相关性质不在本次覆盖范围。

检查：复用固定 Ivy 提交的 value_test、形状/dtype/数值检查，使用公开源测试中静态指定的容差（否则使用原助手默认值）。这不是原 Ivy Hypothesis 策略的完整运行，原测试正文仅作为检查规则出处，不宣称其全部参数/分支已覆盖。

原 oracle 使用 nan_to_num；本适配保留该行为，不据此宣称检查了 NaN/Inf 分布。记录额外非有限位置观察仅供人工复核，不改变原检查结果。

公开输入和 oracle 的组合是本项目新增的受控适配，不是原作者发布的完整测试对。其结果用于限定行为证据，不能证明独立的测试意图迁移保持。
''',encoding='utf-8')
 dump(OUT/'manifest.json',{'cases':cases,'oracle_original_sha256':hashlib.sha256(oracle.read_bytes()).hexdigest(),'oracle_commit':'a701151c85d59c0260a4dbf505479805bdeec00f'})
 shutil.copy2(ROOT/'analysis/scripts/run_composite_adapters.py',OUT/'run_adapters.py')
 (OUT/'README.md').write_text('''# 17组组合函数受控适配

这里实际调用完整原函数，而不是分别调用组件。输入取自 DLLens 公开 sample_inputs；检查器取自公开 Ivy 测试助手，原文保留。

运行需要同一 Python 环境中的 NumPy、PyTorch、TensorFlow，不需要 Ivy 或模型服务。命令：`python run_adapters.py --output results/run.json`。`--case ID` 可限定单组。

不是原 Ivy 测试全量复现：没有执行其 Hypothesis 输入策略、out/inplace/gradient/device 等模式。输入转换仅按值/dtype，结果只适用于实际有效输入。原函数没有的 alpha/dtype 等参数没有被添加。目标异常、源无效、转换失败和检查失败分开记录；所有输出都是技术观察，不是人工标签。

每条记录包含具体输入值、两侧输出/异常、原函数执行行和检查结果。未执行行列在 coverage 中，不等于完整分支覆盖结论。未出现的参数组合不假设已覆盖。
''',encoding='utf-8')
 print(json.dumps({'cases':len(cases),'samples':sum(c['sample_count'] for c in cases)},ensure_ascii=False))
if __name__=='__main__':main()
