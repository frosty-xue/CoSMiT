"""Finish primary reports, one transport retry, and separate parsing sensitivity views."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from collect_public_corpus import ROOT, save, sha
from merge_primary_batches import merge
from recover_structured_verifier_outputs import run as recover_batch
from summarize_experiment import summarize


def retry_view(primary: Path, retries: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    jobs = json.loads((primary / "selected-jobs.json").read_text())
    save(output / "selected-jobs.json", jobs)
    completed = 0
    for job in jobs:
        path = primary / (job["job_id"] + ".json")
        record = json.loads(path.read_text())
        retried = retries / path.name
        primary_status = record["status"]
        if retried.exists():
            attempt = json.loads(retried.read_text())
            if attempt["prompt_sha256"] != record["prompt_sha256"] or primary_status == "completed":
                raise ValueError("Retry is mismatched or repeats a successful primary request")
            if attempt["status"] == "completed":
                record = attempt
            record["retry_file_sha256"] = sha(retried.read_bytes())
            record["retry_status"] = attempt["status"]
        record["primary_status"] = primary_status
        record["primary_file_sha256"] = sha(path.read_bytes())
        save(output / path.name, record)
        completed += record["status"] == "completed"
    save(
        output / "summary.json",
        {
            "logical_requests": len(jobs),
            "completed": completed,
            "failed": len(jobs) - completed,
            "role": "supplementary outcome after at most one transport retry; primary reports unchanged",
        },
    )


def run(output: Path) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "finalize_background_campaign.py").write_bytes(Path(__file__).read_bytes())
    pointer = json.loads((ROOT / "artifacts/baselines/background-current.json").read_text())
    common = Path(pointer["common_campaign_directory"])
    unseen = Path(pointer["unseen_campaign_directory"])
    control = ROOT / "artifacts/baselines/20260916-controls-complete-v3/primary"
    sources = [control, common / "llm-results", unseen / "llm-results"]
    datasets = {
        "controls": (
            ROOT / "artifacts/baselines/20260916-v2/experiment-final",
            control,
            ROOT / "artifacts/baselines/20260916-v2/development/control-key.json",
        ),
        "discovery": (common / "experiment", common / "llm-results", None),
        "unseen": (unseen / "experiment", unseen / "llm-results", None),
    }

    def status(stage: str, state: str, **extra: object) -> None:
        path = output / "status.tmp"
        save(
            path,
            {
                "pid": os.getpid(),
                "stage": stage,
                "state": state,
                "updated_unix": time.time(),
                **extra,
            },
        )
        path.replace(output / "status.json")

    try:
        status("wait-primary-batches", "waiting")
        since = time.time()
        while not all((source / "summary.json").exists() for source in sources):
            for directory in [common, unseen]:
                record = json.loads((directory / "campaign-status.json").read_text())
                if record["state"] == "needs-attention":
                    raise RuntimeError("Upstream campaign needs attention")
            if time.time() - since > 96 * 3600:
                raise TimeoutError("Primary batches exceeded the 96-hour supervisor limit")
            time.sleep(30)
        status("primary-reports", "running")
        merge(sources, output / "primary-all")
        for name, (experiment, source, key) in datasets.items():
            summarize(experiment, output / f"{name}-primary-report", source, key)
            recover_batch(source, output / f"{name}-format-sensitivity")
            summarize(
                experiment,
                output / f"{name}-format-sensitivity-report",
                output / f"{name}-format-sensitivity",
                key,
            )
        jobs = json.loads((output / "primary-all/selected-jobs.json").read_text())
        selected, reasons = [], []
        for job in jobs:
            record = json.loads((output / "primary-all" / (job["job_id"] + ".json")).read_text())
            if record["status"] == "failed" and record.get("error_type") in {
                "TimeoutError",
                "URLError",
            }:
                selected.append(job)
                reasons.append(
                    {
                        "job_id": job["job_id"],
                        "primary_error": record["error_type"],
                        "retry_number": 1,
                        "rationale": "Transport interruption with other requests reaching the same endpoint; wait for all primary batches and increase socket timeout from 90 to 300 seconds. Same model, prompt and token budget.",
                    }
                )
        save(
            output / "retry-plan.json",
            {
                "selected_requests": len(selected),
                "reasons": reasons,
                "excluded_errors": "Unclassified RuntimeError/HTTP, truncated output, invalid JSON and typed-schema failures are not automatically retried",
                "model": "DeepSeek-R1",
                "max_tokens": 4096,
                "temperature": 0,
                "concurrency": 2,
                "maximum_retries_per_request": 1,
            },
        )
        retries = output / "retry-results"
        if selected:
            for case in sorted({j["case_id"] for j in selected}):
                save(
                    output / "retry-requests" / case / "llm-jobs.json",
                    [j for j in selected if j["case_id"] == case],
                )
            status("single-transport-retry", "running", requests=len(selected))
            with (output / "retry.log").open("ab") as log:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-u",
                        str(ROOT / "benchmark/baselines/run_verifier_llm.py"),
                        str(output / "retry-requests"),
                        str(retries),
                        "--execute",
                        "--limit",
                        str(len(selected)),
                        "--model",
                        "DeepSeek-R1",
                        "--timeout",
                        "300",
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            if result.returncode != 0 or not (retries / "summary.json").exists():
                raise RuntimeError(
                    "One retry batch failed as a process; do not repeat automatically"
                )
        else:
            save(retries / "summary.json", {"calls_attempted": 0, "completed": 0, "failed": 0})
        status("supplementary-reports", "running")
        for name, (experiment, source, key) in datasets.items():
            retry_view(source, retries, output / f"{name}-retry-view")
            summarize(
                experiment, output / f"{name}-retry-report", output / f"{name}-retry-view", key
            )
        files = {
            str(path.relative_to(output)): sha(path.read_bytes())
            for path in sorted(output.rglob("*"))
            if path.is_file() and path.name not in {"bundle.integrity.json", "status.json"}
        }
        save(output / "bundle.integrity.json", {"files": files})
        status(
            "full-campaign-reports",
            "completed",
            primary_requests=len(jobs),
            retry_requests=len(selected),
            remaining="Supervisor must inspect final outcomes, update project status/limitations and pause automation; do not claim universal accuracy.",
        )
    except Exception as error:
        status(
            "finalization", "needs-attention", error_type=type(error).__name__, reason=str(error)
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
