"""Run frozen unseen-family cases and queue model calls after the discovery batch."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from collect_public_corpus import ROOT, save


def run(directory: Path, predecessor: Path) -> None:
    directory, predecessor = directory.resolve(), predecessor.resolve()
    with (directory / "campaign.lock").open("x") as stream:
        stream.write(str(os.getpid()))
    (directory / Path(__file__).name).write_bytes(Path(__file__).read_bytes())

    def status(stage: str, state: str, **extra: object) -> None:
        temporary = directory / "campaign-status.tmp"
        save(
            temporary,
            {
                "pid": os.getpid(),
                "stage": stage,
                "state": state,
                "updated_unix": time.time(),
                **extra,
            },
        )
        temporary.replace(directory / "campaign-status.json")

    def stage(name: str, command: list[str], expected: Path) -> None:
        status(name, "running", command=command)
        with (directory / f"{name}.log").open("ab") as log:
            result = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        if result.returncode != 0 or not expected.exists():
            raise RuntimeError(f"Stage {name} failed; preserve output and investigate before retry")
        status(name, "completed")

    scripts = ROOT / "benchmark/baselines"
    experiment, llm = directory / "experiment", directory / "llm-results"
    try:
        stage(
            "unseen-execution",
            [
                sys.executable,
                "-u",
                str(scripts / "run_experiment.py"),
                str(directory / "packet.json"),
                str(experiment),
                "--worker",
                "unseen_worker.py",
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
        status("wait-discovery-model-slots", "waiting", predecessor=str(predecessor))
        since = time.time()
        while not (predecessor / "llm-results/summary.json").exists():
            parent_status = json.loads((predecessor / "campaign-status.json").read_text())
            if parent_status["state"] == "needs-attention":
                raise RuntimeError("Predecessor campaign needs attention")
            os.kill(parent_status["pid"], 0)
            if time.time() - since > 72 * 3600:
                raise TimeoutError("Model slot handoff exceeded 72 hours")
            time.sleep(30)
        stage(
            "unseen-model-batch",
            [
                sys.executable,
                "-u",
                str(scripts / "run_verifier_llm.py"),
                str(experiment),
                str(llm),
                "--execute",
                "--limit",
                "60",
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
            "unseen-campaign",
            "completed",
            interpretation="Finite-domain unseen-family outcomes; final independent-reference metrics still require adjudication",
        )
    except Exception as error:
        status("campaign", "needs-attention", error_type=type(error).__name__, reason=str(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("predecessor", type=Path)
    args = parser.parse_args()
    run(args.directory, args.predecessor)
