"""Summarize primary evaluation batches without counting parser recovery twice."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from collect_public_corpus import ROOT, save


def batch(path: Path, planned: int) -> dict:
    records = []
    reading = 0
    for file in sorted(path.glob("*.json")):
        if len(file.stem) != 20:
            continue
        try:
            value = json.loads(file.read_text())
        except json.JSONDecodeError:
            reading += 1
            continue
        if "job_id" in value:
            records.append(value)
    usage = [r.get("response", {}).get("usage") for r in records]
    known = [u for u in usage if isinstance(u, dict) and isinstance(u.get("total_tokens"), int)]
    return {
        "directory": str(path),
        "planned_requests": planned,
        "returned_records": len(records),
        "records_being_written": reading,
        "batch_finished": (path / "summary.json").exists(),
        "completed_decisions": sum(r["status"] == "completed" for r in records),
        "failed_decisions": sum(r["status"] == "failed" for r in records),
        "failure_types": dict(
            Counter(r.get("error_type", "unknown") for r in records if r["status"] == "failed")
        ),
        "summed_request_seconds": sum(r.get("seconds", 0) for r in records),
        "usage_available_records": len(known),
        "usage_unavailable_records": len(records) - len(known),
        "reported_tokens": sum(u["total_tokens"] for u in known),
        "token_total_complete": len(known) == len(records) and (path / "summary.json").exists(),
        "request_accounting": "Returned request records; started in-flight calls are not yet measurable. Unknown usage is not zero.",
    }


def run(output: Path) -> None:
    pointer = json.loads((ROOT / "artifacts/baselines/background-current.json").read_text())
    primary = [
        ("control-C001", ROOT / "artifacts/baselines/20260916-v2/llm-C001-v2", 5),
        ("control-C002-C010", Path(pointer["run_directory"]) / "control-llm-results", 45),
        ("discovery", Path(pointer["common_campaign_directory"]) / "llm-results", 345),
        ("unseen", Path(pointer["unseen_campaign_directory"]) / "llm-results", 60),
    ]
    batches = {name: batch(path, count) for name, path, count in primary}
    framework = {}
    for name, key in [
        ("discovery", "common_campaign_directory"),
        ("unseen", "unseen_campaign_directory"),
    ]:
        directory = Path(pointer[key])
        path = directory / "execution-report/summary.json"
        if path.exists():
            framework[name] = json.loads(path.read_text())
    public_total = json.loads(
        (ROOT / "artifacts/baselines/20260916-v1/inventory/summary.json").read_text()
    )
    report = {
        "primary_batches": batches,
        "framework_results": framework,
        "all_primary_model_batches_finished": all(b["batch_finished"] for b in batches.values()),
        "planned_primary_requests": sum(b["planned_requests"] for b in batches.values()),
        "returned_primary_records": sum(b["returned_records"] for b in batches.values()),
        "primary_reported_tokens": sum(b["reported_tokens"] for b in batches.values()),
        "public_candidate_inventory": {
            "total_dllens_candidates": 1401,
            "evaluated_discovery_candidates": 69,
            "evaluated_unseen_candidates": 12,
            "remaining_outside_current_registered_domain_adapters": 1320,
            "inventory_available": bool(public_total),
        },
        "independence": "30 operation families; aliases, directions and repeats are correlated, not extra independent samples",
        "non_model_execution_units": {
            "discovery_qualification_pairs": 13248,
            "shared_discovery_comparison_pairs": 13248,
            "shared_unseen_comparison_pairs": 2304,
            "old_control_pairs": 60,
            "original_trunc_replay_pairs": 51,
            "tensorscope_triplets": 192,
            "besser_compatibility_source_forward_calls": 54,
        },
        "cost_scope": "Shared framework execution is counted once per comparison phase, not separately as native time for every verifier. Qualification/setup, debugging and inference alignment have separate budgets. Offline parsing does not add model calls.",
        "performance_boundary": "No extra CoSMiT discovery beyond the same-input DLLens comparator in completed framework comparisons; no unseen counterexample found. No universal preservation or broad intention-accuracy claim.",
    }
    save(output / "status.json", report)
    lines = [
        "# 后台实验汇总",
        "",
        "| 模型批次 | 计划请求 | 已返回记录 | 有效结构化判定 | 失败判定 | 批次结束 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    lines += [
        f"| {name} | {b['planned_requests']} | {b['returned_records']} | {b['completed_decisions']} | {b['failed_decisions']} | {b['batch_finished']} |"
        for name, b in batches.items()
    ]
    lines += [
        "",
        "这些是严格主解析结果；独立的解析敏感性分析不能覆盖主失败。没有token usage的响应保留未知，不按零成本计算。",
        "",
        "公开DLLens库存1,401份，本轮登记域覆盖81份候选（69发现+12未见），另1,320份在当前适配范围之外；不称作全库存实验。统计单位为30个操作家族，正反方向、别名和重复输入不构成独立样本。",
        "",
        "框架阶段：发现集13,248对，CoSMiT和DLLens均检出同一个trunc错误；未见组2,304对，两者均未发现差异。目前无额外检出收益。模型全部结束前不填最终模型对照结论。",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "returned_primary_records": report["returned_primary_records"],
                "planned": report["planned_primary_requests"],
                "all_primary_finished": report["all_primary_model_batches_finished"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
