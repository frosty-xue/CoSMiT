"""Inventory bounded obligations of retained tests; does not create gold labels."""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'datasets/expansion-2026-09-18/assertion-batch-2026-09-28'

# Manual source/adapter inspection, kept separate from experimental outcomes.
SPECIAL={
 'E018':(['输出形状符合 NumPy reshape','静态形状与运行结果形状相符','int64 shape 参数调用'],['原方法无数值相等断言，数值扰动接受不构成丢失','桥接将 shape 参数张量转为 Python 值，不能确认目标原生 int64 参数支持']),
 'E019':(['转置结果与 T/H/mT/mH/adjoint 关系一致'],['运行固定 CPU float32，不覆盖复数共轭分支语义','值桥接复制输入/输出，不验证视图别名或存储共享']),
 'E020':(['省略 perm 时二维默认转置的结果值'],['目标基线失败，不进入扰动拒绝保持评价']),
 'E022':(['去掉单位轴后的形状符合 NumPy','输出值符合 NumPy squeeze'],['测试正文含 GPU 上下文但执行限制为 CPU，不能计为独立 GPU 验证','零值输入和既定形状不能代表全部数值域']),
 'E024':(['axis=0 扩维结果的值与形状','原方法的 axis int32/int64 张量参数兼容性'],['适配器将轴张量转为 Python int，目标原生轴 dtype 兼容性未验证','仅限 axis=0 与长度2零向量']),
 'E025':(['拼接后的各区段等于对应输入','split/chunk 再拼接恢复原张量','最终拼接尺寸'],['值桥接复制了非连续输入，不能验证目标原生非连续布局支持','形状扰动在 narrow 处发生运行异常，未到相关断言','仅第一次操作被扰动，不能推出所有区段断言均有独立敏感性证据']),
 'E026':(['list 与 tuple 两种容器输入的拼接结果一致'],['适配器将 list 和 tuple 都变成 list，原生容器类型义务被归一化','原断言是两次调用的关系检查，不提供完整独立期望值','一次扰动只影响第一次调用，不代表普遍容器语义保持']),
 'E027':(['正负轴 stack 结果一致','stack 输出尺寸','沿新增轴取切片可恢复各输入'],['值桥接不验证存储共享/布局或原生返回对象','仅第一次调用受到扰动，不能扩展为每个 dtype/axis 都有敏感性覆盖']),
 'E028':(['对指定形状、轴、dtype 的 split 后 stack 恢复原数据'],['float8_e5m2 输入在适配器转换时失败','属于 harness 能力限制，不是 counterpart 缺陷','整体方法没有通过，不将此前循环部分成功算成完整通过']),
 'E029':(['双侧/单侧裁剪值','裁剪界限及输入广播结果'],['目标单侧 None 处理失败，后续断言可能未到达','固定 CPU float64；非连续布局经桥接复制，不证明布局语义保持']),
 'E030':(['2×3 输入裁剪结果与期望值接近'],['原方法未覆盖标量输入，不能给标量形状保持标签','本层通过不能推翻 E030 既有标量行为违反'])}


def build(out):
 hashes={}
 def text(p):
  raw=p.read_bytes();hashes[str(p.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest();return raw.decode('utf8')
 def read(p):return json.loads(text(p))
 path=BASE/'verify_batch.py';text(path)
 spec=importlib.util.spec_from_file_location('retained_auditor',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 verified=m.verify_retained()
 matrix={r['case_id']:r for r in verified['matrix']}
 regs=read(BASE/'retained/registration.json')
 cases={c['case_id']:c for c in read(BASE.parent/'candidates.json')}
 records=read(BASE/'retained-executions-v2.json')['records']
 text(BASE/'retained.py')
 result=[]
 for reg in regs:
  cid=reg['case_id']
  if reg['status']!='registered':continue
  c=cases[cid];v=matrix[cid];n=int(cid[1:])
  if n<=16:
   if n%2:
    obligations=['与 NumPy 对应运算参考比较','返回张量及条件 dtype 检查']
    gaps=['替换上游输入生成器，仅扩充索引0、16','固定的有限输入不覆盖所有 dtype/promotion/标量分支','跨框架结果重建为源框架张量，不验证目标原生返回对象类型']
   else:
    obligations=['张量/混合 NumPy 参数调用的值与 NumPy 参考接近','输出形状与参考一致']
    gaps=['替换上游输入生成器，仅扩充索引0、16','also_compare_variables=False，Variable 分支未覆盖','混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义']
  else:obligations,gaps=SPECIAL[cid]
  source=text(BASE/f'retained/{cid}-source.py');target=text(BASE/f'retained/{cid}-target.py')
  for side,body in [('source',source),('target',target)]:assert hashlib.sha256(body.encode()).hexdigest()==reg[side+'_hash']
  def asserts(body):
   return [{'line':x.lineno,'expression':ast.unparse(x)} for x in ast.walk(ast.parse(body)) if isinstance(x,ast.Assert) or isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr.startswith('assert')]
  base=all(s['baseline_qualified'] and s['transparent'] for s in v['scenarios'])
  probes=Counter(p for s in v['scenarios'] for p in s['probes'].values())
  if cid in ['E020','E029']:group='baseline-behavior-failure'
  elif cid=='E028':group='adapter-blocked'
  elif cid=='E026':group='container-obligation-erased-by-adapter'
  elif cid=='E018':group='shape-only-reference-candidate'
  elif cid=='E025':group='value-only-probe-reference-candidate'
  else:group='bounded-value-shape-reference-candidate'
  r={'case_id':cid,'family':c['family'],'entry':reg['entry'],'upstream_file':reg['file'],'upstream_methods':reg['methods'],
     'obligations':obligations,'scope_gaps':gaps,'assertion_sites':{'source':asserts(source),'target':asserts(target)},
     'body_hashes':{s:reg[s+'_hash'] for s in ['source','target']},
     'scenario_count':len(v['scenarios']),'scenarios':v['scenarios'],'baseline_and_transparency_passed':base,
     'probe_outcomes':dict(probes),'review_category':group,
     'bounded_preservation_reference_candidate':base and cid!='E026',
     'native_type_obligations_not_established':True,
     'review_method':'non-blinded source/adapter inspection plus verified recorded executions',
     'independent_gold':False,'full_intent_label':None,'new_model_or_framework_calls':0}
  result.append(r)
 assert len(result)==27
 counts=dict(Counter(r['review_category'] for r in result))
 assert sum(r['baseline_and_transparency_passed'] for r in result)==24
 assert sum(r['bounded_preservation_reference_candidate'] for r in result)==23
 summary={'registered_pairs':27,'unexecuted_aliasing_obligations':['E017','E021','E023'],'category_counts':counts,
          'baseline_and_transparency_passed':24,'bounded_reference_candidates':23,
          'formal_gold_labels':0,'verified_probe_counts':verified['counts'],'new_framework_calls':0,
          'warning':'reference candidates are scope-restricted and selected after observing outcomes; not a blind accuracy test set'}
 out.mkdir(parents=True,exist_ok=False)
 for name,value in [('obligations.json',result),('summary.json',summary),('input-hashes.json',hashes)]:
  (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 labels={'baseline-behavior-failure':'基线行为失败','adapter-blocked':'适配器阻塞','container-obligation-erased-by-adapter':'容器义务被归一化','shape-only-reference-candidate':'仅形状参照候选','value-only-probe-reference-candidate':'数值扰动参照候选','bounded-value-shape-reference-candidate':'限域值/形状参照候选'}
 lines=['# 27 对保留正文测试：义务与证据表','','所有“参照候选”均不是独立 gold。原生类型、布局与存储义务不能由数值桥接自动继承。','','| ID | 家族／入口 | 实际检查义务 | 关键限制 | 当前分组 |','|---|---|---|---|---|']
 for r in result:
  lines.append(f"| {r['case_id']} | {r['family']} / {r['entry']} | {'；'.join(r['obligations'])} | {'；'.join(r['scope_gaps'])} | {labels[r['review_category']]} |")
 (out/'obligations.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 examples=['# 有限范围保持参照材料','','以下为代表性材料，不是新增实验或独立正确标签。','']
 for cid in ['E001','E002','E018','E024','E026','E027','E030']:
  r=next(r for r in result if r['case_id']==cid)
  examples += [f'## {cid}：{r["entry"]}','','检查义务：'+'；'.join(r['obligations']),'','限制：'+'；'.join(r['scope_gaps']),'',f"判定分组：{labels[r['review_category']]}。",'','```json',json.dumps(r['scenarios'],ensure_ascii=False,indent=2),'```','']
  examples += ['断言位置：','']+[f'- 源正文第 {a["line"]} 行：`{a["expression"]}`' for a in r['assertion_sites']['source']]+['']
 (out/'reference-cases.md').write_text('\n'.join(examples)+'\n',encoding='utf8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);build(p.parse_args().output)
