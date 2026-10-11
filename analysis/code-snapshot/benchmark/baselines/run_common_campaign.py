"""Background campaign with recorded stages and no duplicate model batches."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from collect_public_corpus import ROOT, save


def run(directory: Path, control: Path) -> None:
    directory = directory.resolve()
    started = time.time()
    status_file = directory / "campaign-status.json"
    with (directory / "campaign.lock").open("x") as lock:
        lock.write(str(os.getpid()))
    (directory / "run_common_campaign.py").write_bytes(Path(__file__).read_bytes())

    def status(stage: str, state: str, **extra: object) -> None:
        temporary = status_file.with_suffix(".tmp")
        save(
            temporary,
            {
                "pid": os.getpid(),
                "stage": stage,
                "state": state,
                "started_unix": started,
                "updated_unix": time.time(),
                **extra,
            },
        )
        temporary.replace(status_file)

    def stage(name: str, command: list[str], result: Path) -> None:
        if result.exists():
            status(name, "already-completed")
            return
        status(name, "running", command=command)
        with (directory / f"{name}.log").open("ab") as log:
            process = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        if process.returncode != 0 or not result.exists():
            raise RuntimeError(
                f"Stage {name} failed; see preserved log; no automatic duplicate launch"
            )
        status(name, "completed")

    scripts = ROOT / "benchmark/baselines"
    experiment = directory / "experiment"
    llm = directory / "llm-results"
    try:
        stage(
            "common-execution",
            [
                sys.executable,
                "-u",
                str(scripts / "run_experiment.py"),
                str(directory / "packet.json"),
                str(experiment),
                "--workers",
                "2",
                "--timeout",
                "180",
            ],
            experiment / "summary.json",
        )
        stage(
            "execution-report",
            [
                sys.executable,
                str(scripts / "summarize_experiment.py"),
                str(experiment),
                str(directory / "execution-report"),
            ],
            directory / "execution-report/summary.json",
        )
        # The previous run owns the two model slots until its summary exists.
        status("wait-existing-control-model-batch", "waiting", control=str(control))
        waiting_since = time.time()
        while not (control / "control-llm-results/summary.json").exists():
            metadata = json.loads((control / "background-process.json").read_text())
            os.kill(metadata["pid"], 0)
            if time.time() - waiting_since > 12 * 3600:
                raise TimeoutError("Existing control batch exceeded 12-hour handoff window")
            time.sleep(30)
        stage(
            "full-model-batch",
            [
                sys.executable,
                "-u",
                str(scripts / "run_verifier_llm.py"),
                str(experiment),
                str(llm),
                "--execute",
                "--limit",
                "345",
                "--model",
                "DeepSeek-R1",
                "--timeout",
                "90",
            ],
            llm / "summary.json",
        )
        stage(
            "final-report",
            [
                sys.executable,
                str(scripts / "summarize_experiment.py"),
                str(experiment),
                str(directory / "final-report"),
                "--llm",
                str(llm),
            ],
            directory / "final-report/summary.json",
        )
        status(
            "common-discovery-campaign",
            "completed",
            scope="69 public discovery candidates; remaining model adapters and unseen-family evaluation tracked separately",
        )
    except Exception as error:
        status("campaign", "needs-attention", error_type=type(error).__name__, reason=str(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("control", type=Path)
    args = parser.parse_args()
    run(args.directory, args.control)
