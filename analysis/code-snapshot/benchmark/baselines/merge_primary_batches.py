"""Merge completed, disjoint primary request batches without making new model calls."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from collect_public_corpus import save, sha
from verification_ports import aggregate_checks, digest


def merge(sources: list[Path], output: Path) -> None:
    all_jobs, records, provenance, seen = [], [], [], set()
    for source in sources:
        if not (source / "summary.json").exists():
            raise ValueError("Source batch has not finished")
        for job in json.loads((source / "selected-jobs.json").read_text()):
            if job["job_id"] in seen:
                raise ValueError("Overlapping logical requests cannot be silently merged")
            if digest(job["prompt"]) != job["prompt_sha256"]:
                raise ValueError("Frozen prompt was modified")
            path = source / (job["job_id"] + ".json")
            record = json.loads(path.read_text())
            if (
                record["prompt_sha256"] != job["prompt_sha256"]
                or record["case_id"] != job["case_id"]
                or record["kind"] != job["kind"]
            ):
                raise ValueError("Response does not match selected request")
            seen.add(job["job_id"])
            all_jobs.append(job)
            records.append((record, path))
            provenance.append(
                {
                    "job_id": job["job_id"],
                    "source": str(path.resolve()),
                    "sha256": sha(path.read_bytes()),
                }
            )
    output.mkdir(parents=True, exist_ok=False)
    save(output / "selected-jobs.json", all_jobs)
    for record, path in records:
        (output / path.name).write_bytes(path.read_bytes())
    aggregates = []
    for case in sorted({r["case_id"] for r, _ in records}):
        checks = {
            r["kind"]: r.get("parsed", {}).get("valid") for r, _ in records if r["case_id"] == case
        }
        original = [checks.get("intenttester-source-tdl"), checks.get("intenttester-target-api")]
        aggregates.append(
            {
                "case_id": case,
                "intenttester-verifier-port": aggregate_checks(original),
                "intenttester-target-tdl-extension": aggregate_checks(
                    original + [checks.get("intenttester-target-tdl-extension")]
                ),
            }
        )
    save(
        output / "configuration.json",
        {
            "role": "primary-batch-union",
            "source_configurations": [
                {
                    "directory": str(s),
                    "configuration": json.loads((s / "configuration.json").read_text()),
                }
                for s in sources
            ],
            "additional_model_calls": 0,
        },
    )
    save(output / "provenance.json", provenance)
    save(
        output / "summary.json",
        {
            "calls_attempted": len(records),
            "completed": sum(r["status"] == "completed" for r, _ in records),
            "failed": sum(r["status"] == "failed" for r, _ in records),
            "failure_types": dict(
                Counter(
                    r.get("error_type", "unknown") for r, _ in records if r["status"] == "failed"
                )
            ),
            "aggregates": aggregates,
            "additional_model_calls": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    merge(args.sources, args.output)
