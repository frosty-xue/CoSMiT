"""Merge reusable original results with expansion results, preserving missingness."""
import argparse
import json
from datetime import datetime
from collections import Counter
from pathlib import Path
from verification_ports import ROOT, aggregate_checks


def read(p):
    return json.loads(p.read_text(encoding='utf8'))


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def summarize(campaign):
    originals = read(ROOT / 'artifacts/analysis/research-data-2026-10-09/candidate-methods.json')
    local = read(campaign / 'local-verifier-results.json')
    docter = {r['case_id']: r for r in read(campaign / 'docter-110.json')}
    jobs = read(campaign / 'jobs-manifest.json')
    attempts = []
    for p in sorted((campaign / 'physical-attempts').glob('*.json')):
        attempts.append(read(p))
    views = {}
    for view in ('primary', 'retry-view'):
        rows = []
        for old in originals[view]:
            rows.append({'case_id': old['case_id'], 'cohort': 'original-80',
                         'methods': {k: v for k, v in old.items() if k not in
                                     ('case_id', 'partition', 'family', 'intenttester-complete-pair')},
                         'reference_label': None})
        for r in local:
            cid = r['case_id']
            selected = {}
            request_states = {}
            for job in [j for j in jobs if j['case_id'] == cid]:
                records = [a for a in attempts if a['job_id'] == job['job_id']]
                if records:
                    chosen = records[0] if view == 'primary' else next((a for a in records if a['status'] == 'completed'), records[-1])
                    selected[job['kind']] = chosen
                    request_states[job['kind']] = chosen['status']
                else:
                    request_states[job['kind']] = 'not-run'
            checks = [selected.get(k, {}).get('parsed', {}).get('valid') for k in
                      ('intenttester-source-tdl', 'intenttester-target-api', 'intenttester-target-tdl-extension')]
            methods = {
                'cosmit-registered-clauses': r['cosmit-core-recorded-operation'],
                'dllens-port': r['dllens-dense-port'], 'self-test': r['self-test'], 'target-binding': r['target-binding'],
                'intenttester-verifier-port': aggregate_checks(checks[:2]) if any(k in selected for k in
                    ('intenttester-source-tdl', 'intenttester-target-api')) else 'not-run',
                'intenttester-target-tdl-extension': aggregate_checks(checks) if selected else 'not-run',
            }
            for kind in ('direct-llm', 'trace-llm'):
                item = selected.get(kind)
                methods[kind] = item.get('parsed', {}).get('verdict', item['status']) if item else 'not-run'
            rows.append({'case_id': cid, 'cohort': 'expansion-30', 'methods': methods,
                         'request_statuses': request_states, 'reference_label': None,
                         'historical_behavior_audit': r['historical_expansion_behavior_status']})
        for r in rows:
            d = docter[r['case_id']]
            r['methods']['docter-historical-constraints'] = ('violated' if d['counts'].get('violated') else
                'satisfied' if d['counts'].get('satisfied') == 64 else 'undetermined')
        assert len(rows) == 110 and len({r['case_id'] for r in rows}) == 110 and all(r['case_id'] != 'D0028' for r in rows)
        views[view] = rows
    counts = {view: {k: dict(Counter(r['methods'][k] for r in rows)) for k in rows[0]['methods']}
              for view, rows in views.items()}
    save(campaign / 'combined-110-results.json', views)
    save(campaign / 'combined-110-counts.json', counts)
    diagnostics = [read(p) for p in campaign.glob('diagnostic-*.json')]
    usage = [a.get('response', {}).get('usage') for a in attempts + diagnostics]
    stats = {'physical_attempts': len(attempts), 'diagnostic_attempts': len(diagnostics),
             'total_model_requests_including_diagnostics': len(attempts) + len(diagnostics),
             'completed_attempts': sum(a['status'] == 'completed' for a in attempts),
             'reported_tokens': sum(u.get('total_tokens', 0) or 0 for u in usage if u),
             'usage_unavailable_attempts': sum(not u for u in usage)}
    save(campaign / 'cost-current.json', stats)
    job_groups = {}
    for a in attempts:
        job_groups.setdefault(a['job_id'], []).append(a)
    effective = [next((a for a in group if a['status'] == 'completed'), group[-1]) for group in job_groups.values()]
    repairs = sorted(p.parent.name for p in campaign.glob('repair-*/configuration.json'))
    completion = {'planned_jobs': 150, 'attempted_jobs': len(effective),
                  'successful_jobs': sum(a['status'] == 'completed' for a in effective),
                  'failed_jobs': sum(a['status'] != 'completed' for a in effective),
                  'not_attempted_jobs': 150-len(effective), 'supplemental_rounds': repairs,
                  'counts_by_kind': {k: dict(Counter(a['status'] for a in effective if a['kind'] == k))
                                     for k in sorted({a['kind'] for a in effective})}}
    save(campaign / 'coverage-current.json', completion)
    if repairs:
        latest = campaign / repairs[-1]
        end_file = latest / 'summary.json'
        progress_file = latest / 'progress.json'
        phase = read(end_file) if end_file.exists() else read(progress_file) if progress_file.exists() else {'planned': len(read(latest / 'configuration.json').get('selected', [])), 'statuses': {}}
        planned = phase.get('planned', 0)
        statuses = phase.get('statuses', {})
        finished = sum(statuses.values())
        status_text = ('本轮补跑已结束' if end_file.exists() else '本轮补跑尚未结束（未生成结束标记）')
        status_lines = [f'# {status_text}', '', f'更新时间：{datetime.now().astimezone().isoformat(timespec="seconds")}', '',
                        f'- 本轮已处理：{finished}/{planned} 个请求。',
                        f'- 本轮成功：{statuses.get("completed", 0)}；失败：{statuses.get("failed", 0)}。',
                        f'- 尚待本轮处理结束：{max(0, planned-finished)}。', '',
                        '**本轮结束不代表全部基线齐全。** Direct LLM / Trace LLM 的暂停和未执行请求仍单独保留。', '',
                        '本文件由报告更新进程约每分钟刷新；若更新时间长时间不变，请检查后台进程。',
                        f'结束标记：`{repairs[-1]}/summary.json`。']
        (campaign / 'STATUS.md').write_text('\n'.join(status_lines)+'\n', encoding='utf8')
    text = '''# 110 个候选：基线实验进度（2026-10-10）

## 范围

复用 research-data/2026-09-17 中排除 D0028 后的 80 个候选；扩充仅使用 datasets/expansion-2026-09-18。
扩充集调用现有 prepare_llm_jobs 的五类提示模板，全部 64 个输入和三次重复观察均保留。
源参考输出、人工标签、CoSMiT/DLLens 判断没有放入模型提示。
当前评估范围为登记操作契约；不等于完整迁移测试断言的意图保持。

## 已完成的本地计算

| 项目 | 扩充 30 组 | 合并 110 组 |
| --- | --- | --- |
| CoSMiT 当前核心，保存观察回放 | 26 支持、2 反驳、2 未决 | 106 支持、2 反驳、2 未决 |
| DLLens 固定 dense 比较器 | 28 未发现数值差异、2 未决 | 108 未发现数值差异、2 未决 |
| 正常执行自测试 | 28 通过、2 失败 | 108 通过、2 失败 |
| DocTer 历史字面约束 | 9 满足、10 违反、11 未决 | 45 满足、11 违反、54 未决 |

DocTer 重新计算了全部 110 个候选的逐输入结果，不重复调用模型。98 个候选有约束文件；12 个缺少已冻结映射。
历史约束来自 PyTorch 1.5 / TensorFlow 2.1，与实际框架版本的兼容性未建立。
DocTer 的“违反”表示其历史约束检查结果，不能直接作为迁移意图违反或人工真值。

## 一项必须保留的实现差异

之前的行为审计发现 E020、E029、E030 三个问题，此结论仍成立。
但本次实际调用 src/cosmit/engine/certification.py 的 evaluate，并沿用已有 worker 的调用绑定门槛，
E020 会得到未决：perm=None 在真正调用 permute 之前发生参数解包异常，目标调用列表为空，核心先检查绑定而未进入异常违反分支。
因此不能把“三个已复现的行为问题”直接写成“当前 CoSMiT 核心检测出三个”。
当前核心反驳 E029、E030；E020 和 E021 未决。没有为了提高本批结果修改核心。
DLLens 这里仅运行固定数值比较器；E020/E029 异常没有数值比较，不能据此声称完整 DLLens 漏报。

## 模型实验与重试

模型 DeepSeek-R1，temperature=0、top_p=1、presence_penalty=0、max_tokens=4096、并发 2。
补充轮次以各自 configuration.json 为准：repair-round-02 对已证实 length 截断的两个请求单独使用 8192；不能将该预算结果当作原始 4096 预算结果。
初始 E001 五类请求因连接错误失败，额外一次短请求重试也发生 SSLEOFError；全部记录保留。
用户随后授权失败重试：仅连接/超时类故障最多四次物理尝试（含已有尝试），间隔 5/15/30 秒。
不因模型给出否定结论而重试，不自动重试正常返回后的截断、格式错误。
首次尝试与含重试视图分别写入 combined-110-results.json，不能混合当作同一固定预算实验。

原批次进度见 progress.json；补跑后的累计覆盖见 coverage-current.json，补跑进度见 repair-*/progress.json。
physical-attempts 保存全部物理请求；requests 仅是原批次缓存，补跑后的有效结果以 combined-110-results.json 的 retry-view 为准。
repair-*/offline-format-recovery.json 单独保存完整 fenced JSON 的离线恢复，不覆盖严格解析结果。
当前进度不是完成报告。缺失 usage 不代表零费用；准确率、召回率仍需独立限域参考标签。
'''
    text += '\n生成此报告时，扩充集调用记录：\n\n```json\n' + json.dumps(stats, indent=2) + '\n```\n'
    text += '\n累计请求覆盖（含补跑）：\n\n```json\n' + json.dumps(completion, indent=2) + '\n```\n'
    (campaign / 'REPORT.md').write_text(text, encoding='utf8')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign', type=Path)
    summarize(p.parse_args().campaign)
