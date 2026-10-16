"""One table and one review sheet per candidate, with all v3/v4 evidence."""
import hashlib,json,re,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'analysis/annotation-package-2026-10-16-v4'
OUT=ROOT/'analysis/annotation-package-2026-10-16'
def write(p,s):p.write_text(s,encoding='utf-8')
def dump(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir()
 obsolete=['behavior-review.md','constructed-intent-review.md','public-test-review.md','controlled-adaptation-review.md','test-pair-intake.md']
 for name in ['candidates','shared','tools','public-tests','controlled-adapters']:
  shutil.copytree(SRC/name,OUT/name,ignore=shutil.ignore_patterns(*obsolete,'__pycache__'))
 index=json.loads((SRC/'candidate-index.json').read_text(encoding='utf-8'))
 manifest=json.loads((SRC/'material-manifest.json').read_text(encoding='utf-8'))
 rows=[]
 for c in index:
  cid=c['candidate_id'];p=OUT/'candidates'/cid;adapted=c.get('controlled_whole_function_adaptation_available',False)
  links=f'''- [两端现成测试、完整原文件及出处](../../public-tests/candidates/{cid}/README.md)
- [源操作](source-operation.py) · [目标操作](target-operation.py)
- [既有登记输入](inputs.json) · [既有观察](observations.json) · [声明范围](declared-behavior-scope.json)
'''
  if adapted:links+=f'''- [完整函数适配说明](../../controlled-adapters/cases/{cid}/README.md)
- [完整函数本轮运行记录](../../controlled-adapters/cases/{cid}/observations.json)
- [运行入口](../../controlled-adapters/run_adapters.py)（`--case {cid}`）
'''
  if c['test_pair_available']:links+='- [早期构造源测试](source-test.py) · [早期构造目标测试](target-test.py) · [构造登记](test-registration.json)：辅助证据，非历史迁移输出。\n'
  status=(f'两端公开测试＋完整函数受控适配，已运行 {c["controlled_sample_count"]} 条固定公开样本。' if adapted else '两端公开 API/运算符测试已提供；本轮未运行这些公开测试。')
  write(p/'README.md',f'''# {cid}: {c['source_api']} → {c['target_calls']}

**唯一填写入口：[本组标注工作表](review.md)。** [返回110组总表](../../ANNOTATIONS.md)

{status}

## 全部材料

{links}
## 使用说明

将以上材料共同用于本组复核，不需分别填写 v3/v4 表。标签与证据范围写在同一工作表中。公开测试输入域和断言可能不同；完整函数适配记录只支持其实际固定样本及公开检查器覆盖的性质。旧观察与本轮 sample_index 属于不同实验，引用时注明文件。
''')
  write(p/'review.md',f'''# {cid} 统一标注工作表

[全部材料](README.md) · [110组主表](../../ANNOTATIONS.md)

## 一、评估对象与材料资格

- 标注者／日期：
- 源测试文件、函数、参数场景：
- 目标测试文件、函数、参数场景：
- 对应依据（API、功能、输入条件；不要求历史迁移记录）：
- 与本组 source-operation.py / target-operation.py 的对应关系：
- 输入域、dtype、shape、版本、设备、容差及参考检查：
- 公共 helper、fixture、输入生成器是否已阅读：
- 材料资格：待核查（可评／部分可评／需补材料／不适用，说明理由）

本组材料状态：{status}

## 二、行为是否保持

- 行为标签：待标注（保持／不保持／证据不足／不适用）
- 判断针对的实现及输入范围：
- 代码、输入和运行证据（路径＋行号／input_index 或 sample_index）：
- 结论依据或有效反例：
- 未覆盖分支、参数和性质（设备、梯度、共享存储等）：

## 三、测试意图是否保持

- 源测试要检查的目标／性质：
- 源检查依据（断言、预期异常、输入构造、公共检查器及行号）：
- 目标测试对应检查及其范围：
- 意图标签：待标注（保持／不保持／证据不足／不适用）
- 保留、遗漏或改变了哪些检查；依据：
- 多个义务结论不同则逐项追加 obligation_id 和范围，不以多数票合并：

## 四、综合记录与缺口

- 尚缺材料或待补跑场景：
- 与其他义务／场景存在的差异：
- 回填主表的范围与证据摘要：

行为与意图分别判断，不相互推出。技术检查通过/失败不是人工标签。{'本组完整函数适配使用DLLens固定输入和共用公开检查器，未运行原Ivy全部随机策略；可以支持限定行为判断，不能单独证明独立意图迁移保持。' if adapted else '现成测试来自独立公开来源，尚需核对其输入和检查目标，不把材料存在当作已保持。'}

## 五、分歧复核（完成独立标注后）

- 标注者A原标签及依据：
- 标注者B原标签及依据：
- 分歧点／追加证据：
- 复核结论、限定范围、复核者及日期：
''')
  rows.append(f'|[{cid}](candidates/{cid}/review.md)|`{c["source_api"]}`|`{c["target_calls"]}`|'+(f'两端测试＋完整函数适配（{c["controlled_sample_count"]}条）' if adapted else '两端现成测试')+'|待核查|待标注|待标注|—|—|')
  c['review_unit_id']=cid;c['review_sheet']=f'candidates/{cid}/review.md'
 for m in manifest:m.update(review_unit_id=m['candidate_id'],review_sheet=f'candidates/{m["candidate_id"]}/review.md',annotation_table='ANNOTATIONS.md')
 dump(OUT/'candidate-index.json',index);dump(OUT/'material-manifest.json',manifest)
 write(OUT/'ANNOTATIONS.md','''# 110组统一标注表

每组只填这一行和链接的同一份工作表，不再分v3/v4或公开测试/适配表。所有材料已归入对应候选入口。

行为、意图可选：保持／不保持／证据不足／不适用。材料资格可选：可评／部分可评／需补材料／不适用。待标注不是结论。结论必须注明场景/范围及证据文件，不将不同实现或不同输入上的结论强行合并。

|候选／工作表|源API|目标调用|现有材料|材料资格|行为是否保持|意图是否保持|范围／证据|标注者／日期|
|---|---|---|---|---|---|---|---|---|
'''+ '\n'.join(rows)+'\n')
 write(OUT/'README.md','''# CoSMiT 统一标注包（2026-10-16）

**只使用一张主表：[ANNOTATIONS.md](ANNOTATIONS.md)。每组只填写 candidates/ID/review.md 一份工作表。** 这份包已合并此前v3的公开测试和v4的完整函数适配，不需要分别打开旧版或重复填写。

## 包含的材料

|候选范围|材料|
|---|---|
|全部110组|两端公开API测试、原操作、来源和上下文、既有输入与观察|
|其中17组组合目标|另附完整函数受控适配及332条固定公开样本的本轮运行记录|
|其中27组|保留早期构造测试原文，作为辅助证据并注明来源|

上述分组仅说明来源与覆盖范围，所有标注均在同一主表及候选工作表中完成。未新填人工标签，旧包没有覆盖。

## 如何填写

1. 每位标注者使用独立副本，在总表点击候选ID。
2. 从同一组README查看全部两端测试、原函数和运行记录，选择具体测试场景和评估范围。
3. 分别判断行为和意图，写明依据。二者互不推出；通过/失败不自动等于保持/不保持。
4. 回填总表。不同义务结论不一致，保留工作表内的逐项记录，不强行归成一个无范围的标签。
5. 独立标注后，在同一工作表末尾记录分歧与复核。

## 证据解释

行为保持指明确输入/环境下API或完整实现的行为对应；测试意图保持指源测试要检查的性质是否仍被目标测试检查。

接受现成公开测试按对应API配对，不要求历史迁移日志。Ivy测试可能使用其前端和后端，并非直接调用当前DLLens包装函数；判断时需写明对应关系。

17组适配实际调用完整原函数，使用DLLens公开固定输入和Ivy公开检查器，不是原Ivy随机策略的全量运行。其输入转换只保留值/dtype；共用检查器不能独立证明意图保持。现成历史组合测试未取得的事实不因新增适配而改变。

旧登记观察与新增适配观察分属不同实验；以文件路径和编号引用，不能混同 input_index 与 sample_index。适配记录为技术证据，不是人工标准答案。

## 文件组织与交付

- candidates/ID/：唯一工作表review.md、材料入口README.md、原操作与既有材料。
- public-tests/：两端现成公开测试的完整原文、摘录、出处和公共助手；只读证据，不另填表。
- controlled-adapters/：17组完整函数适配代码与本轮记录；只读证据，不另填表。
- candidate-index.json / material-manifest.json：逐组材料索引。

仅返回填好的ANNOTATIONS.md、各组review.md和补充的reviewer-evidence即可。SHA256.json为交付初始文件清单，标注后变化正常。原测试依赖原仓库环境；摘录用于阅读，不能假定独立可执行。
''')
 # All prior Python and observation evidence must be preserved byte-for-byte.
 kept=0
 for f in SRC.rglob('*'):
  if f.is_file() and (f.suffix=='.py' or f.name=='observations.json'):
   assert (OUT/f.relative_to(SRC)).read_bytes()==f.read_bytes();kept+=1
 assert len(rows)==110 and sum(c.get('controlled_whole_function_adaptation_available',False) for c in index)==17
 hashes={f.relative_to(OUT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in OUT.rglob('*') if f.is_file() and f.name!='SHA256.json'}
 dump(OUT/'SHA256.json',hashes)
 broken=[];links=0
 for f in OUT.rglob('*.md'):
  for target in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
   if '://' in target or target.startswith('#'):continue
   links+=1
   if not (f.parent/target.split('#')[0]).exists():broken.append([str(f),target])
 assert not broken,broken
 assert len(list((OUT/'candidates').glob('*/review.md')))==110
 zpath=OUT.with_suffix('.zip')
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(OUT.rglob('*')):
   if f.is_file():z.write(f,OUT.name+'/'+f.relative_to(OUT).as_posix())
 with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
 validation={'main_annotation_tables':1,'candidate_review_sheets':110,'adapted_candidates':17,'preserved_code_and_observation_files':kept,'links_checked':links,'broken_links':broken,'zip_crc':'pass','zip_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()}
 dump(ROOT/'analysis/annotation-package-validation-2026-10-16.json',validation)
 print(json.dumps(validation,ensure_ascii=False))
if __name__=='__main__':main()
