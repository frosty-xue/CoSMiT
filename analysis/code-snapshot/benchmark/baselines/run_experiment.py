"""Run fixed candidates, local verification ports, and prepare label-free LLM jobs."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from verification_ports import ROOT, check_docter, digest, prepare_llm_jobs, upstream


def summarize(trace: dict[str, Any]) -> dict[str, str]:
    rows = trace.get("records", [])
    base = {
        "self-test": "undetermined",
        "target-binding": "undetermined",
        "dllens-port": "undetermined",
        "cosmit-registered-clauses": "undetermined",
    }
    if not rows or trace.get("status") != "completed":
        return base
    if any(r.get("status") == "invalid-source-test" for r in rows):
        return dict.fromkeys(base, "invalid-source-test")
    if any(r.get("status") == "invalid-source-assumption" for r in rows):
        return dict.fromkeys(base, "invalid-source-assumption")
    if all(r.get("status") == "invalid-input" for r in rows):
        return dict.fromkeys(base, "invalid-input")
    completed = [r for r in rows if r.get("status") == "executed"]
    if len(completed) == len(rows):
        base["self-test"] = "passed"
        base["target-binding"] = (
            "observed" if all(r["target"]["calls"] for r in rows) else "not-observed"
        )
        base["dllens-port"] = (
            "no-difference-on-tested-inputs"
            if all(r["dllens_agrees"] for r in rows)
            else "difference-observed"
        )
    # Three actual executions, same input, same clause and same value/shape/dtype.
    for index in {r["input_index"] for r in completed}:
        group = [r for r in completed if r["input_index"] == index]
        if len(group) != 3 or {r["repeat"] for r in group} != {0, 1, 2}:
            continue
        signatures = [
            digest(
                {
                    side: {k: r[side][k] for k in ["value", "dtype", "shape"]}
                    for side in ["source", "target"]
                }
            )
            for r in group
        ]
        violated = [
            {c["clause_id"] for c in r["clause_results"] if c["outcome"] == "violation"}
            for r in group
        ]
        if len(set(signatures)) == 1 and set.intersection(*violated):
            base["cosmit-registered-clauses"] = "refuted"
            break
    if (
        completed
        and len(completed) == len(rows)
        and all(
            r["clause_results"] and all(c["outcome"] == "pass" for c in r["clause_results"])
            for r in completed
        )
    ):
        base["cosmit-registered-clauses"] = "supported-on-tested-inputs"
    return base


def execute(
    packet_path: Path,
    output: Path,
    python: Path,
    workers: int,
    timeout: int,
    worker_name: str = "experiment_worker.py",
) -> None:
    if worker_name not in {"experiment_worker.py", "unseen_worker.py"}:
        raise ValueError("Unregistered execution worker")
    packet = json.loads(packet_path.read_text())
    ids = [c["id"] for c in packet["cases"]]
    if len(ids) != len(set(ids)) or not all(i.isalnum() for i in ids):
        raise ValueError("duplicate or unsafe candidate IDs")
    budget = packet["budget"]
    allowed_inputs = 64 if packet.get("schema_version") == 3 else 2
    if budget != {
        "inputs_per_case": allowed_inputs,
        "executions_per_input": 3,
        "max_pairs_per_case": 3 * allowed_inputs,
    }:
        raise ValueError("unsupported execution budget; use a new protocol version")
    if any(len(c["inputs"]) != allowed_inputs for c in packet["cases"]):
        raise ValueError("candidate inputs do not match frozen budget")
    output.mkdir(parents=True, exist_ok=False)
    (output / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    code_paths = [
        Path(__file__),
        Path(__file__).with_name(worker_name),
        Path(__file__).with_name("verification_ports.py"),
        Path(__file__).with_name("source_property_reference.py"),
        ROOT / "src/cosmit/engine/certification.py",
    ]
    if worker_name == "unseen_worker.py":
        code_paths.append(Path(__file__).with_name("unseen_properties.py"))
    configuration = {
        "packet_sha256": digest(packet),
        "python": str(python.resolve()),
        "workers": workers,
        "timeout_seconds_per_candidate": timeout,
        "worker_name": worker_name,
        "code_hashes": {str(p.relative_to(ROOT)): digest(p.read_text()) for p in code_paths},
        "reference_key_loaded": False,
        "method_reference_only": ["TransFuzz"],
    }
    (output / "configuration.json").write_text(json.dumps(configuration, indent=2) + "\n")
    snapshot = output / "implementation"
    snapshot.mkdir()
    for path in code_paths:
        (snapshot / path.name).write_bytes(path.read_bytes())

    def one(case: dict[str, Any]) -> dict[str, Any]:
        directory = output / case["id"]
        directory.mkdir()
        case_file = directory / "case.json"
        case_file.write_text(json.dumps(case))
        result_path = directory / "execution.json"
        command = [
            str(python.resolve()),
            str(Path(__file__).with_name(worker_name)),
            str(case_file.resolve()),
            str(result_path.resolve()),
        ]
        env = {k: os.environ[k] for k in ["PATH", "LANG", "TMPDIR"] if k in os.environ}
        env.update(HOME=str(directory.resolve()), OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        started = time.perf_counter()
        try:
            process = subprocess.run(
                command,
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            (directory / "stdout.txt").write_text(process.stdout)
            (directory / "stderr.txt").write_text(process.stderr)
            trace = (
                json.loads(result_path.read_text())
                if process.returncode == 0 and result_path.exists()
                else {
                    "case_id": case["id"],
                    "status": "worker-error",
                    "exit_code": process.returncode,
                }
            )
        except subprocess.TimeoutExpired:
            trace = {"case_id": case["id"], "status": "timeout"}
        trace["wall_seconds"] = time.perf_counter() - started
        # No schema metadata/description is treated as a semantic verdict.
        if case.get("docter_file"):
            schema = yaml.safe_load(upstream("docter", case["docter_file"]))
            constraints = [check_docter(schema, args) for args in case["inputs"]]
        else:
            constraints = [
                {"state": "undetermined", "reason": "no-frozen-schema-for-source-api"}
                for _ in case["inputs"]
            ]
        verdicts = summarize(trace)
        jobs = prepare_llm_jobs(case, trace)
        record = {
            "case_id": case["id"],
            "group": case["group"],
            "origin": case["origin"],
            "execution": trace,
            "verdicts": verdicts,
            "docter": constraints,
            "llm_status": "prepared-not-run",
        }
        (directory / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        (directory / "llm-jobs.json").write_text(json.dumps(jobs, indent=2) + "\n")
        print(case["id"], trace["status"], verdicts["cosmit-registered-clauses"], flush=True)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(one, packet["cases"]))
    with (output / "candidate-table.csv").open("w") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["case_id", "group", "origin", "execution_status", *records[0]["verdicts"]],
        )
        writer.writeheader()
        writer.writerows(
            {
                **{k: r[k] for k in ["case_id", "group", "origin"]},
                "execution_status": r["execution"]["status"],
                **r["verdicts"],
            }
            for r in records
        )
    summary = {
        "partition": packet["partition"],
        "formal_eligible": packet["formal_eligible"],
        "cases": len(records),
        "source_groups": len({r["group"] for r in records}),
        "paired_executions": sum(r["execution"].get("paired_executions", 0) for r in records),
        "execution_statuses": dict(Counter(r["execution"]["status"] for r in records)),
        "cosmit_states": dict(Counter(r["verdicts"]["cosmit-registered-clauses"] for r in records)),
        "llm_jobs_prepared": 5 * len(records),
        "llm_calls_executed": 0,
        "interpretation": "Finite registered-clause experiment; partition and formal eligibility are explicit; no universal preservation claim.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--python", type=Path, default=ROOT / "tmp/public-system-envs/dllens-smoke/bin/python"
    )
    parser.add_argument("--workers", type=int, choices=[1, 2], default=2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--worker",
        choices=["experiment_worker.py", "unseen_worker.py"],
        default="experiment_worker.py",
    )
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("positive timeout required")
    execute(args.packet, args.output, args.python, args.workers, args.timeout, args.worker)
