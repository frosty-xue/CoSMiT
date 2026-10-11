"""Prepare current prompts from existing observations without repeating executions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verification_ports import digest, prepare_llm_jobs


def prepare(experiment: Path, output: Path) -> None:
    packet = json.loads((experiment / "packet.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in packet["cases"]:
        record_path = experiment / case["id"] / "record.json"
        record = json.loads(record_path.read_text())
        target = output / case["id"]
        target.mkdir()
        jobs = prepare_llm_jobs(case, record["execution"])
        (target / "llm-jobs.json").write_text(json.dumps(jobs, indent=2) + "\n")
        records.append({"case_id": case["id"], "observation_record_hash": digest(record)})
    manifest = {
        "execution_packet_hash": digest(packet),
        "records": records,
        "prompt_code_hash": digest(Path(__file__).with_name("verification_ports.py").read_text()),
        "framework_executions_added": 0,
    }
    (output / "configuration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {5 * len(records)} requests from existing observations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.experiment, args.output)
