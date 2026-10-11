"""Join execution and LLM results; control keys are opened only after verification."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from verification_ports import aggregate_checks, prepare_llm_jobs


def summarize(experiment: Path, output: Path, llm: Path | None, control_key: Path | None) -> None:
    output.mkdir(parents=True, exist_ok=False)
    packet = json.loads((experiment / "packet.json").read_text())
    answers = {}
    failed = set()
    expected_jobs = {}
    for case in packet["cases"]:
        record = json.loads((experiment / case["id"] / "record.json").read_text())
        expected_jobs.update({j["job_id"]: j for j in prepare_llm_jobs(case, record["execution"])})
    if llm:
        selected = json.loads((llm / "selected-jobs.json").read_text())
        for job in selected:
            if expected_jobs.get(job["job_id"], {}).get("prompt_sha256") != job["prompt_sha256"]:
                raise ValueError("model request belongs to a different candidate/context version")
            path = llm / (job["job_id"] + ".json")
            if not path.exists():
                continue
            record = json.loads(path.read_text())
            if record["prompt_sha256"] != job["prompt_sha256"]:
                raise ValueError("response/request provenance mismatch")
            if record["status"] == "completed":
                answers[(job["case_id"], job["kind"])] = record["parsed"]
            else:
                failed.add((job["case_id"], job["kind"]))
    rows = []
    controls = {r["case_id"]: r for r in json.loads(control_key.read_text())} if control_key else {}
    if controls and packet.get("formal_eligible"):
        raise ValueError("development control keys cannot label a formal experiment")
    for case in packet["cases"]:
        record = json.loads((experiment / case["id"] / "record.json").read_text())
        row = {"case_id": case["id"], "source_group": case["group"], **record["verdicts"]}
        for method in ["direct-llm", "trace-llm"]:
            row[method] = answers.get((case["id"], method), {}).get(
                "verdict", "failed" if (case["id"], method) in failed else "not-run"
            )
        checks = [
            answers.get((case["id"], method), {}).get("valid")
            for method in [
                "intenttester-source-tdl",
                "intenttester-target-api",
                "intenttester-target-tdl-extension",
            ]
        ]
        row["intenttester-verifier-port"] = aggregate_checks(checks[:2])
        row["intenttester-target-tdl-extension"] = aggregate_checks(checks)
        schema_states = [r["state"] for r in record["docter"]]
        row["docter-historical-constraints"] = (
            "violated"
            if "violated" in schema_states
            else "undetermined"
            if "undetermined" in schema_states
            else "satisfied"
        )
        row["control_check"] = (
            str(row["cosmit-registered-clauses"] == controls[case["id"]]["expected_cosmit"])
            if case["id"] in controls
            else "not-evaluated"
        )
        rows.append(row)
    with (output / "method-matrix.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "candidate_count": len(rows),
        "source_group_count": len({r["source_group"] for r in rows}),
        "partition": packet["partition"],
        "formal_eligible": packet["formal_eligible"],
        "counts": {
            method: dict(Counter(r[method] for r in rows))
            for method in rows[0]
            if method not in {"case_id", "source_group"}
        },
        "accuracy_metrics": "not-computed: this report has no independent formal reference labels",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = [
        "# 共同实验结果",
        "",
        f"候选 {len(rows)} 条；源 API 家族 {summary['source_group_count']} 个。",
        "",
        "| 方法 | 状态计数 |",
        "| --- | --- |",
    ]
    lines += [
        f"| {name} | {json.dumps(counts, ensure_ascii=False)} |"
        for name, counts in summary["counts"].items()
    ]
    lines += [
        "",
        f"分区：{packet['partition']}。未运行、失败和未决保留在表内；本表不计算正式准确率。",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--llm", type=Path)
    parser.add_argument("--control-key", type=Path)
    args = parser.parse_args()
    summarize(args.experiment, args.output, args.llm, args.control_key)
