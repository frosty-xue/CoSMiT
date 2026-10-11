"""Build an evidence inventory, not independent gold, from approved data sources.

Uses hash-matched DLLens code; never executes counterpart code or requests models.
"""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / 'datasets/expansion-2026-09-18'
BATCH = EXP / 'assertion-batch-2026-09-28'
COMBINED = ROOT / 'artifacts/analysis/combined-data-2026-10-09'
PRIORITY = ['E020', 'E029', 'E030', 'D0011', 'D0012', 'D0030', 'H003', 'H008', 'H010', 'H011', 'H012']
NOTES = {
    'E020': ('默认 perm=None 应执行轴序反转；保留方法 testTranspose2DAuto 明确检查转置后的 2×3→3×2 内容。', 'counterpart 对 None 解包；保留正文实验也在目标操作执行阶段失败，未到达后续断言。', '可作为行为违反及构造操作替换测试的基线失败证据；不能称断言被删除。', '复核默认参数义务、操作替换适配和源规格；完整历史迁移测试来源仍缺。'),
    'E029': ('test_clamp 分别断言双侧裁剪、仅 min、仅 max 和广播结果。', '目标对 None 无条件 tf.cast；单侧裁剪在保留正文实验中触发目标执行错误。', '可作为行为违反及构造操作替换测试的基线失败证据；现有断言表达式仍保留。', '复核合法可选界限、CPU/dtype 固定设置与适配过程；完整历史迁移测试来源仍缺。'),
    'E030': ('动态条款要求保持输出形状；保留的 testClipByValue 使用 2×3 输入并比较期望值。', '目标 new_ones(1) 引入长度为 1 的维度；标量见证为 []→[1]。保留方法没有标量场景。', '行为形状违反成立于已重放输入；不能用当前 2×3 测试证明标量检查意图丢失。', '寻找真实覆盖标量形状义务的源测试及其迁移版本；新增构造测试必须单列，不能冒充原测试。'),
    'D0011': ('登记域为有限 float32/64 输入 [-8,8]，检查 exp 值、形状与类型。', '代码为 torch.exp→tf.exp；目标 API 检查给出 false，但公开记录没有理由。', '现有代码与通过记录不能裁定该 false 的具体原因；未确认误报。', '补原始否定理由与精确提示，核对环境/调用上下文；补原测试断言与迁移来源。'),
    'D0012': ('登记域为 [-8,8]，检查 expm1 值、形状与类型及已固定容差。', '目标实际是 tf.exp(x)-1，不是直接 tf.math.expm1；存在需要核验的小量消减精度问题。', '这是代码审查线索，不是已验证的新反例；是否超过固定绝对/相对容差尚未验证。', '补模型理由；在已登记容差下检查近零输入，保留独立数值参考；补源/迁移测试断言。'),
    'D0030': ('有限浮点输入 [-1,1]，检查 acos 值、形状与类型。', '源端 TDL 检查 false；源函数只有 tf.acos 调用，没有测试断言。', '可能涉及声明条款与函数正文的对应方式；模型具体原因未知。', '补模型理由，复核条款是否应由函数或外部测试 harness 承担；补真实断言。'),
    'H003': ('行列式域为 1×1 至 4×4 严格对角占优浮点矩阵；独立参考为排列求和。', '源端 TDL 检查 false；torch.det 函数正文没有断言，公开记录没有理由。', '有限执行支持仍保留；不能把模型否定解释为行列式计算错误。', '补理由并分别核对矩阵域、参考、容差及原测试的检查义务。'),
    'H008': ('登记的是二维稠密浮点矩阵；转置、伴随、稀疏标志均 false，output_type=None。', '目标有额外标志分支，但忽略 output_type；模型目标 API 检查 false。', '域外分支问题与当前域内判定必须分开；未确认该模型判断针对哪个条件。', '补精确提示/理由，核对模型是否获得了范围约束；另列可选参数审查，不回填当前域错误标签。'),
    'H010': ('登记矩阵形状均为二维，要求对角线求和及其输出形状。', '目标对 rank>2 的结果额外 view；该分支不在当前输入域。模型否定来自源 TDL 检查。', '高维形状是另一个审查线索，不能拿它解释源 TDL 的 false 或判当前域错误。', '补源 TDL 否定理由和源断言；高维行为若研究，应另立扩展域与实验。'),
    'H011': ('有限小整数浮点输入，有效轴；exclusive=False、reverse=False。', 'Direct LLM 为 invalid-assumption，目标 TDL 为 false；正文也包含域外 exclusive/reverse 分支。', '两次否定不等于两份独立真实标签；没有理由，无法确定争议前提。', '优先恢复两条理由及提示，核对条款、函数正文与输入域；补真实测试断言。'),
    'H012': ('有限小整数浮点输入，有效轴；exclusive=False、reverse=False。', 'exclusive 分支使用 cumprod[:-1]，切片固定第一维；当前登记域未启用该分支。', '域外切片与 axis 的关系值得另查，但不能据此把当前域的通过记录标成错误。', '补目标 API 否定理由；按 axis/标志分开建立范围，真实源/迁移断言仍缺。'),
}


def main(out, checkout):
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def code(path):
        raw = path.read_bytes()
        hashes[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        return raw.decode('utf8')

    def assertion_sites(text):
        tree = ast.parse(text)
        return [{'line': n.lineno, 'expression': ast.unparse(n)} for n in ast.walk(tree)
                if isinstance(n, ast.Assert) or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith('assert')]

    merged = read(COMBINED/'metrics.json')
    for rel, expected in read(COMBINED/'input-hashes.json').items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == expected, rel
    negative = merged['initial_model_evidence_unchanged']['negative_judgments']
    requests = read(ROOT/'research-data/2026-09-17/model-primary.json')
    registry = {r['case_id']: r for r in read(BATCH/'retained/registration.json')}
    intake = {r['case_id']: r for r in read(BATCH/'intake.json')}
    review = {r['case_id']: r for r in read(BATCH/'review-status.json')}
    retained = {r['case_id']: r for r in merged['assertion_evidence_same_30_candidates']['retained']['matrix']}
    dynamic = {r['case_id']: r for r in read(EXP/'runs/2026-09-20-dynamic-v3/case-results.json')}
    witnesses = read(EXP/'runs/2026-09-20-dynamic-v3/counterexamples.json')
    rows = []
    for part in ['discovery', 'unseen']:
        path = ROOT/f'research-data/2026-09-17/{part}/cases.json'
        for c in read(path):
            if c['id'] == 'D0028':
                continue
            p = checkout/c['upstream_path']
            original = read(p)
            snippets = {side: original['counterparts'][c[side]['framework']] for side in ['source', 'target']}
            for side, text in snippets.items():
                assert hashlib.sha256(text.encode()).hexdigest() == c[side+'_code_sha256'], (c['id'], side)
            rows.append({'case_id': c['id'], 'family': c['group'], 'batch': part,
                         'origin': c['origin'], 'provenance': str(p), 'export_record': str(path),
                         'contract': c['contract'], 'source_target_code': snippets,
                         'assertion_sites_in_counterparts': {s: assertion_sites(t) for s,t in snippets.items()},
                         'code_hash_verified': True,
                         'source_test_status': 'counterpart-functions-only; original assertion-bearing test not established',
                         'historical_migrated_test_pair_established': False,
                         'behavior_evidence': 'supported-on-tested-inputs',
                         'retained_assertion_evidence': None,
                         'missing': ['原始带断言测试及迁移测试来源', '独立标签依据与复核'],
                         'evaluation_use': 'behavior-description-only; intent-gold-not-ready'})
    for c in read(EXP/'candidates.json'):
        cid = c['case_id']; reg = registry[cid]
        snippets = {s: code(EXP/c[s]['code_path']) for s in ['source','target']}
        for s,t in snippets.items():
            assert hashlib.sha256(t.encode()).hexdigest() == c[s]['code_sha256']
        bodies = {}
        for side in ['source','target']:
            p = BATCH/f'retained/{cid}-{side}.py'
            if p.exists():
                text = code(p)
                assert hashlib.sha256(text.encode()).hexdigest() == reg[side+'_hash']
                bodies[side] = {'path': str(p), 'assertions': assertion_sites(text)}
        status = dynamic[cid]['status']
        rows.append({'case_id':cid,'family':c['family'],'batch':'expansion',
                     'origin':'published-counterpart plus newly constructed test wrappers/operation substitutions',
                     'provenance':c['upstream_url'],'source_target_code':snippets,'code_hash_verified':True,
                     'assertion_sites_in_counterparts':{s:assertion_sites(t) for s,t in snippets.items()},
                     'source_test_status':reg['status'],'upstream_test_registration':reg,
                     'diagnostic_source_anchor':intake[cid]['source_anchor'],
                     'diagnostic_excluded_obligations':intake[cid]['excluded_obligations'],
                     'retained_bodies':bodies,'historical_migrated_test_pair_established':False,
                     'behavior_evidence':status,'dynamic_result':dynamic[cid],
                     'witness_input_indices':[w['input_index'] for w in witnesses if w['case_id']==cid],
                     'retained_assertion_evidence':retained[cid], 'previous_review':review[cid],
                     'missing':['外部历史迁移测试来源或明确限定构造迁移评价','完整义务及适配过程的独立复核'],
                     'evaluation_use':'behavior-case-study-and-bounded-assertion-evidence' if bodies else 'behavior-evidence; retained-obligations-unresolved'})
    for r in rows:
        cid = r['case_id']
        r['priority'] = cid in PRIORITY
        r['model_negative_decisions'] = [x for x in negative if x['case_id']==cid]
        r['negative_request_references'] = [{k:x[k] for k in ['job_id','kind','prompt_sha256','original_record_file_sha256','decision']} for x in requests if x['case_id']==cid and any(n['kind']==x['kind'] for n in r['model_negative_decisions'])]
        r['model_reasons_available_in_export'] = False
        r['independent_behavior_label'] = None
        r['independent_full_intent_label'] = None
        r['review_status'] = 'evidence-inventory-reviewed; independent-adjudication-pending'
        r['blinded_review'] = False
        if cid in NOTES:
            r['priority_review'] = dict(zip(['obligation','finding','interpretation','next_evidence'],NOTES[cid]))
    assert len(rows)==len({r['case_id'] for r in rows})==110
    assert sum(r['priority'] for r in rows)==11
    stats = {'candidates':110,'hash_verified_counterpart_functions':220,
             'counterparts_with_assertion_syntax':sum(bool(v) for r in rows for v in r['assertion_sites_in_counterparts'].values()),
             'retained_body_pairs':sum(bool(r.get('retained_bodies')) for r in rows),
             'historical_migrated_test_pairs_established':sum(r['historical_migrated_test_pair_established'] for r in rows),
             'independent_full_intent_labels':0,'priority_cases':11,
             'behavior_evidence':dict(collections.Counter(r['behavior_evidence'] for r in rows))}
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('inventory.json',rows),('summary.json',stats),('input-hashes.json',hashes),
                      ('adjudication-template.json',[{'case_id':r['case_id'],'scope':None,'obligations':None,'behavior_label':None,'intent_label':None,'evidence_refs':[],'reviewer':None,'reviewer_kind':None,'blind_to_method_outputs':None,'decision_reason':None} for r in rows])]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# 测试证据与标签表（110 个候选）','','本表是证据盘点，不是独立 gold。标签字段保持空值；本轮已经接触方法输出，不属于盲审。D0028 与历史 controls 排除。','','| 候选 | 家族 | 行为记录 | 测试证据 | 完整意图标签 |','|---|---|---|---|---|']
    names={'supported-on-tested-inputs':'有限输入支持','supported-on-qualified-inputs':'合格输入支持','discrepancy-replayed':'行为违反已重放','undetermined-binding':'绑定未决'}
    for r in rows:
        evidence='对应函数；原断言未建立' if r['batch']!='expansion' else '上游正文＋构造操作替换' if r.get('retained_bodies') else '上游义务已登记；别名义务未解决'
        lines.append(f"| {r['case_id']}{' ★' if r['priority'] else ''} | {r['family']} | {names[r['behavior_evidence']]} | {evidence} | 待独立裁决 |")
    (out/'inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    details=['# 11 个优先候选的证据复核','','本轮为代码及既有记录核查，未新增框架执行、模型调用或独立标签。静态风险线索不计为新增反例。','']
    for cid in PRIORITY:
        r=next(r for r in rows if r['case_id']==cid)
        details += [f'## {cid} · {r["family"]}','']
        for label,key in [('检查义务','obligation'),('核查发现','finding'),('当前可用结论','interpretation'),('缺少与下一步','next_evidence')]:
            details += [f'**{label}：** {r["priority_review"][key]}','']
        if r['model_negative_decisions']:
            details += ['否定判断：'+ '；'.join(x['kind']+' '+json.dumps(x['decision']) for x in r['model_negative_decisions']),'']
        if r.get('retained_bodies'):
            details += ['保留正文：'+ '；'.join(f'[{s}]({Path(v["path"]).as_posix()})' for s,v in r['retained_bodies'].items()),'']
        if r['batch']!='expansion':
            details += [f'哈希匹配的原始对应代码：[本地来源]({Path(r["provenance"]).as_posix()})','']
        for side,text in r['source_target_code'].items():
            details += [f'### {side} counterpart','', '```python',text,'```','']
    (out/'priority-review.md').write_text('\n'.join(details)+'\n',encoding='utf8')
    print(json.dumps(stats,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--checkout',type=Path,default=Path('F:/codes/python/DLLens'));a=p.parse_args();main(a.output,a.checkout)
