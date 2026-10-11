"""Build a reviewer-facing, decision-free annotation packet for the 110 candidates."""
import ast
import gzip
import hashlib
import json
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/annotation-package-2026-10-11'
UNITS = ROOT / 'analysis/results/unified-evaluation-units-2026-10-10'
NEW = ROOT / 'research-data/2026-10-11'


def read(p):
    return json.loads(p.read_text(encoding='utf8'))


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def copy(p, q):
    q.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, q)
    assert p.read_bytes() == q.read_bytes()


def observation(r):
    return {k: r[k] for k in ('status', 'value', 'shape', 'dtype', 'error', 'message', 'calls') if k in r}


def main():
    OUT.mkdir(exist_ok=False)
    original = {c['id']: c for part in ('discovery', 'unseen') for c in read(ROOT / f'research-data/2026-09-17/{part}/cases.json') if c['id'] != 'D0028'}
    expansion = {c['case_id']: c for c in read(NEW / 'expansion-2026-09-18/candidates.json')}
    normal = defaultdict(list)
    for part in ('discovery', 'unseen'):
        with gzip.open(ROOT / f'research-data/2026-09-17/{part}/executions.jsonl.gz', 'rt', encoding='utf8') as f:
            for line in f:
                r = json.loads(line)
                if r['case_id'] in original:
                    normal[r['case_id']].append({k: r[k] for k in ('input_index', 'repeat', 'versions')} |
                                              {side: observation(r[side]) for side in ('source', 'target')})
    for cid in expansion:
        trace = read(NEW / f'baseline-campaign/prepared/{cid}/observations.json')
        normal[cid] = [{k: r[k] for k in ('input_index', 'repeat')} | {'versions': trace['versions']} |
                       {side: observation(r[side]) for side in ('source', 'target')} for r in trace['records']]
    rows, inventory = [], []
    for cid in sorted(set(original) | set(expansion)):
        unit = read(UNITS / f'units/{cid}/unit.json')
        folder = OUT / 'candidates' / cid
        folder.mkdir(parents=True)
        old = cid in original
        c = original[cid] if old else expansion[cid]
        prepared = c if old else read(NEW / f'baseline-campaign/prepared/{cid}/case.json')
        source_api = c['source']['api'] if old else c['source_api']
        target_api = c['target']['api'] if old else ', '.join(c['target']['syntactic_calls'])
        name = source_api + ' → ' + target_api
        for side in ('source', 'target'):
            copy(UNITS / f'units/{cid}/{side}-operation.py', folder / f'{side}-operation.py')
        inputs = prepared['inputs']
        assert len(inputs) == 64 and len(normal[cid]) == 192
        write(folder / 'inputs.json', [{'input_index': i, 'arguments': a} for i, a in enumerate(inputs)])
        write(folder / 'observations.json', normal[cid])
        contract = {k: v for k, v in prepared['contract'].items() if k != 'evidence'}
        write(folder / 'declared-behavior-scope.json', contract)
        provenance = {'candidate_id': cid, 'source_api': source_api, 'target_calls': target_api,
                      'source': {k: c['source'][k] for k in ('framework', 'entry')},
                      'target': {k: c['target'][k] for k in ('framework', 'entry')},
                      'cohort': unit['cohort'],
                      'counterpart_url': ('https://github.com/maybeLee/DLLens/blob/0f617e92c34d60bfdd3bc06d80c17d938879ed9c/' + c['upstream_path']) if old else c['upstream_url'],
                      'operation_sha256': {side: hashlib.sha256((folder / f'{side}-operation.py').read_bytes()).hexdigest() for side in ('source', 'target')},
                      'test_pair_available': bool(unit['test']),
                      'test_pair_origin': 'constructed operation substitution; shared source-framework harness' if unit['test'] else None}
        write(folder / 'metadata.json', provenance)
        specs = prepared['contract'].get('evidence', []) if old else []
        if old:
            write(folder / 'source-specification-links.json', specs)
        else:
            fw = c['source']['framework']
            doc = read(NEW / f'expansion-2026-09-18/runs/2026-09-20-dynamic-v3/source-{fw}.json')
            (folder / 'source-api-documentation.txt').write_text(doc['source_specifications'].get(source_api, 'No captured API documentation.'), encoding='utf8')
        if unit['test']:
            test = unit['test']
            for side in ('source', 'target'):
                copy(UNITS / test[f'{side}_file'], folder / f'{side}-test.py')
            reg = test['registration']
            # Preserve source locations and execution setup, not past evaluation outcomes.
            write(folder / 'test-registration.json', {k: reg[k] for k in
                ('file', 'class', 'methods', 'entry', 'paths', 'kind', 'parameters', 'source_framework')})
            scope = read(UNITS / test['input_scope'])
            if 'frozen_scenarios' in scope:
                scope['frozen_scenarios'] = [{k: p[k] for k in ('input_index', 'arguments') if k in p} for p in scope['frozen_scenarios']]
            write(folder / 'test-input-scope.json', scope)
            copy(UNITS / test['upstream_snapshot'], OUT / test['upstream_snapshot'])
            test_text = ('本候选有构造的源/目标测试正文。它不是历史迁移测试；两端共用源框架断言环境，操作返回值经桥接。'
                         '仅阅读两个正文不足以判断适配语义，还须检查共享 runner、注册信息和输入范围。\n\n'
                         '- [源测试](source-test.py) / [目标测试](target-test.py)\n'
                         '- [注册与入口](test-registration.json) / [测试输入范围](test-input-scope.json)\n'
                         f'- [上游完整文件](../../{test["upstream_snapshot"]})\n'
                         '- [执行适配上下文（只读源码）](../../shared/retained-runner-context.txt)\n')
        else:
            test_text = ('当前没有已配对、可直接评价的源/目标测试正文。操作函数不等于测试；不得由 API 名称或输出一致直接填“意图保持”。'
                         '如果无法取得充分证据，可以将意图标为“证据不足”，并记录缺少什么。\n')
        leads = unit.get('source_test_leads', [])
        if leads:
            neutral = [{k: r[k] for k in ('framework', 'file', 'class', 'method', 'start', 'end', 'commit', 'matched_symbols') if k in r} for r in leads]
            write(folder / 'unverified-source-test-leads.json', neutral)
            for lead in leads:
                dest = OUT / lead['file']
                if not dest.exists():
                    copy(UNITS / lead['file'], dest)
            test_text += '\n[源测试检索线索](unverified-source-test-leads.json)仅按 API 文本引用得到，可能是辅助操作；没有确认与本候选配对。路径相对于标注包根目录。\n'
        text = f'''# {cid}：{name}

## 先看这些材料

- [源操作代码](source-operation.py) / [目标操作代码](target-operation.py)
- [来源、框架和函数入口](metadata.json)
- [64 个登记输入](inputs.json) / [声明的行为范围](declared-behavior-scope.json)
- [所有登记输入的原始执行观察](observations.json)：按 input_index、repeat 对齐，共三次重复；不含方法判断。

声明的契约是待核查的实验设定，不是正确答案。有限输入一致不等于全输入域等价。not-executed 仅表示无该次观察，不能解释为目标失败。

## 测试意图材料

{test_text}

## 标注记录（由标注者填写）

- 标注者／日期：
- 行为评估范围（默认只针对登记输入；若扩展需明确说明）：
- 源端适用性（有效／部分无效／无效／证据不足）及依据：
- 行为保持（保持／不保持／证据不足／不适用）：
- 行为依据（代码行、输入编号、观察或规格出处；如有反例，请列出）：
- 源测试意图（用自己的话描述具体检查目标，不直接抄 API 功能）：
- 意图评估范围（哪个测试、哪项义务、哪些参数）：
- 意图保持（保持／不保持／证据不足／不适用）：
- 意图依据（断言、异常预期、数据流、适配逻辑、必要的追加检查）：
- 置信度／待补证据：
- 第二位复核者与分歧处理（如有）：

最终标签同时回填根目录 [标注表](../../ANNOTATIONS.md)。允许行为与意图的两列取不同结论。
'''
        (folder / 'README.md').write_text(text, encoding='utf8')
        rows.append(f'| [{cid}](candidates/{cid}/README.md) | {name} | {"构造测试对" if unit["test"] else "暂无配对测试"} | 待标注 | 待标注 | — | — | — | — |')
        inventory.append(provenance)
    assert len(rows) == 110 and sum(x['test_pair_available'] for x in inventory) == 27
    copy(UNITS / 'shared/retained-runner.py', OUT / 'shared/retained-runner-context.txt')
    copy(UNITS / 'shared/registered-upstream-provenance.json', OUT / 'shared/registered-upstream-provenance.json')
    (OUT / 'ANNOTATIONS.md').write_text('''# CoSMiT 候选标注表（110 组）

每位标注者使用独立副本，先阅读 README.md。所有标签初始留为“待标注”；该值不等于“不保持”。
允许填写：**保持／不保持／证据不足／不适用**。行为与意图分别判断，不相互推导。
“不适用”必须给出原因；材料缺失通常应填“证据不足”。标签范围默认是每个候选明确登记的范围，不能表述为任意输入上的等价。
理由可简写，详细证据填写各候选 README 的标注记录，并在表格中引用。

| 候选／材料入口 | 候选名称（源 API → 目标调用） | 测试材料 | 行为是否保持 | 意图是否保持 | 行为依据／范围 | 意图依据／源意图 | 标注者 | 日期 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
''' + '\n'.join(rows) + '\n', encoding='utf8')
    write(OUT / 'candidate-index.json', inventory)
    print(f'Prepared {len(rows)} candidates and 27 constructed test pairs at {OUT}')


if __name__ == '__main__':
    main()
