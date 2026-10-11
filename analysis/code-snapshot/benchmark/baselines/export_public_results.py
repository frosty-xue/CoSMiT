"""Export observed results without credentials, copied programs, or model prose."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "artifacts/baselines"
FINAL = BASE / "20260916-final-v1"


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(value):
    if isinstance(value, dict):
        return {
            k: sanitize(v)
            for k, v in value.items()
            if k not in {"code", "source_code", "target_code", "prompt", "public_sample_inputs"}
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return value.replace(str(ROOT) + "/", "").replace(str(Path.home()), "<HOME>")
    return value


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize(value), ensure_ascii=False, indent=2) + "\n")


def records(path: Path):
    return [read(p) for p in sorted(path.glob("*.json")) if len(p.stem) == 20]


def export(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name in [
        "summary.json",
        "cost.json",
        "method-matrices.json",
        "request-outcomes-by-kind.json",
    ]:
        save(output / name, read(BASE / "20260917-completion-v1" / name))
    save(output / "upstream-lock.json", read(ROOT / "benchmark/baselines/frozen-manifest.json"))
    configurations = {
        "controls": BASE / "20260916-v2/llm-C001-v2/configuration.json",
        "discovery": BASE / "20260916-common-v3/llm-results/configuration.json",
        "unseen": BASE / "20260916-unseen-v1/llm-results/configuration.json",
        "retry": FINAL / "retry-results/configuration.json",
    }
    configuration_keys = {
        "model",
        "checkpoint_verified",
        "request_limit",
        "workers",
        "automatic_retries",
        "socket_timeout",
        "transport_hash",
        "runner_hash",
        "ports_hash",
    }
    for label, path in configurations.items():
        save(
            output / f"configuration-{label}.json",
            {k: v for k, v in read(path).items() if k in configuration_keys},
        )
    parts = {
        "controls": BASE / "20260916-v2/experiment-final",
        "discovery": BASE / "20260916-common-v3/experiment",
        "unseen": BASE / "20260916-unseen-v1/experiment",
    }
    pair_counts = {}
    for part, directory in parts.items():
        cases, executions = [], []
        for file in sorted(directory.glob("*/record.json")):
            result, case = read(file), read(file.with_name("case.json"))
            public_case = sanitize(case)
            public_case["original_case_file_sha256"] = sha(file.with_name("case.json"))
            public_case["source_code_sha256"] = hashlib.sha256(
                case["source"]["code"].encode()
            ).hexdigest()
            public_case["target_code_sha256"] = hashlib.sha256(
                case["target"]["code"].encode()
            ).hexdigest()
            public_case["verdicts"] = result["verdicts"]
            public_case["original_record_file_sha256"] = sha(file)
            cases.append(public_case)
            execution = read(file.with_name("execution.json"))
            for entry in execution["records"]:
                executions.append(
                    {"case_id": case["id"], "versions": execution["versions"], **entry}
                )
        save(output / part / "cases.json", cases)
        with (
            (output / part / "executions.jsonl.gz").open("wb") as stream,
            gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped,
        ):
            for entry in executions:
                zipped.write((json.dumps(sanitize(entry), ensure_ascii=False) + "\n").encode())
        pair_counts[part] = len(executions)
    for label, directory in [
        ("primary", FINAL / "primary-all"),
        ("retry", FINAL / "retry-results"),
    ]:
        rows = []
        for row in records(directory):
            public = {
                k: row[k]
                for k in ["job_id", "case_id", "kind", "prompt_sha256", "status", "seconds"]
            }
            public["error_type"] = row.get("error_type")
            public["rejection_reason"] = row.get("reason")
            public["decision"] = {
                k: v for k, v in row.get("parsed", {}).items() if k in {"valid", "verdict"}
            }
            public["usage"] = row.get("response", {}).get("usage")
            public["original_record_file_sha256"] = sha(directory / (row["job_id"] + ".json"))
            public["finish_reasons"] = [
                c.get("finish_reason") for c in row.get("response", {}).get("choices", [])
            ]
            rows.append(public)
        save(output / f"model-{label}.json", rows)
    for part in parts:
        for view in ["format-sensitivity", "retry-view"]:
            rows = []
            for row in records(FINAL / f"{part}-{view}"):
                rows.append({k: row[k] for k in ["job_id", "case_id", "status"]})
            save(output / part / f"{view}.json", rows)
    supplements = {
        "besser-source": BASE / "20260916-model-adapters-v1/besser-source-execution/summary.json",
        "besser-cnn-rnn": BASE / "20260916-model-adapters-v1/cnn-rnn-source-diagnosis.json",
        "tensorscope": BASE / "20260916-model-adapters-v1/tensorscope/validation.json",
        "image-pairs": BASE / "20260916-image-model-pairs-v1/validation.json",
        "initial-pairs": ROOT
        / "artifacts/dataset-sources/20260916-v1/pair-validation/summary.json",
    }
    for label, file in supplements.items():
        save(output / "supplements" / f"{label}.json", read(file))
    corpus = ROOT / "artifacts/dataset-sources/20260916-v1"
    save(output / "additional-sources.lock.json", read(corpus / "sources.lock.json"))
    for label, file in {
        "alexnet": BASE / "20260916-image-model-pairs-v1/alexnet.json",
        "vgg16": BASE / "20260916-image-model-pairs-v1/vgg16.json",
        "lstm": corpus / "pair-validation/lstm-aligned.json",
        "tf-tutorial": corpus / "pair-validation/tf_tutorial-aligned.json",
    }.items():
        save(output / "supplements" / f"{label}-observations.json", read(file))
    save(
        output / "publication.json",
        {
            "schema_version": 1,
            "pair_counts": pair_counts,
            "raw_artifact_manifest_sha256": sha(FINAL / "bundle.integrity.json"),
            "scope": "Observed data and decision audit; not a standalone exact rerun package",
            "omissions": [
                "credentials",
                "machine paths",
                "third-party program and prompt bodies",
                "model prose and reasoning",
                "environments and weights",
                "blinded-review answer keys",
            ],
            "raw_data": "Original archives retained locally unchanged; published records link via SHA256",
            "transfuzz": "method reference only; not a baseline",
        },
    )
    save(
        output / "SHA256.json",
        {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()},
    )
    verify(output)


def verify(output: Path) -> None:
    for name, expected in read(output / "SHA256.json").items():
        assert sha(output / name) == expected, name
    counts = {}
    for part, expected in [("controls", 60), ("discovery", 13248), ("unseen", 2304)]:
        with gzip.open(output / part / "executions.jsonl.gz", "rt") as stream:
            rows = [json.loads(line) for line in stream]
        assert len(rows) == expected
        assert len({(r["case_id"], r["input_index"], r["repeat"]) for r in rows}) == expected
        counts[part] = len(rows)
    primary, retry = read(output / "model-primary.json"), read(output / "model-retry.json")
    assert len(primary) == 455 and len(retry) == 33
    index = {r["job_id"]: r for r in primary}
    assert len(index) == 455
    assert len({r["job_id"] for r in retry}) == 33
    for row in retry:
        before = index[row["job_id"]]
        assert before["error_type"] in {"TimeoutError", "URLError"}
        assert before["prompt_sha256"] == row["prompt_sha256"]
    assert Counter(r["status"] for r in primary) == {"completed": 278, "failed": 177}
    assert Counter(r["status"] for r in retry) == {"completed": 17, "failed": 16}
    print(
        json.dumps(
            {
                "verified_pairs": counts,
                "primary_requests": len(primary),
                "retry_requests": len(retry),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    (verify if args.verify else export)(args.output)
