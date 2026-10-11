"""Validate registered source properties, then evaluate unchanged public counterparts."""

from __future__ import annotations

import argparse
import json
import platform
import time
from collections import Counter
from pathlib import Path

from collect_public_corpus import save, sha
from source_property_reference import make_inputs, scalar_reference, valid_input
from verification_ports import dllens_comparator


def run(corpus: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import tensorflow as tf
    import torch

    torch.set_num_threads(1)
    properties = {r["id"]: r for r in json.loads((corpus / "source-properties.json").read_text())}
    cases = json.loads((corpus / "dllens-candidates.json").read_text())
    code_files = [
        Path(__file__),
        Path(__file__).with_name("source_property_reference.py"),
        Path(__file__).with_name("collect_public_corpus.py"),
        Path(__file__).with_name("verification_ports.py"),
    ]
    snapshot = output / "implementation"
    snapshot.mkdir()
    for path in code_files:
        (snapshot / path.name).write_bytes(path.read_bytes())
    save(
        output / "configuration.json",
        {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "tensorflow": tf.__version__,
            "seed": 20260916,
            "inputs_per_candidate": 64,
            "repetitions": 3,
            "partition": "discovery-not-holdout",
            "source_before_target": True,
            "property_hash": sha((corpus / "source-properties.json").read_bytes()),
            "candidate_hash": sha((corpus / "dllens-candidates.json").read_bytes()),
            "code_hashes": {p.name: sha(p.read_bytes()) for p in code_files},
            "formal_accuracy_eligible": False,
        },
    )
    inputs = {
        family: make_inputs(prop["domain"], 20260916, np) for family, prop in properties.items()
    }
    save(output / "inputs.json", inputs)
    compare = dllens_comparator(np)

    def invoke(code: str, framework: str, arg: str, array: object) -> tuple[dict, object]:
        namespace = {"np": np, "tf": tf, "torch": torch}
        try:
            exec(compile(code, "frozen-public-counterpart", "exec"), namespace)  # noqa: S102 -- execute inspected, versioned public code
            tensor = (
                torch.from_numpy(array.copy())
                if framework == "pytorch"
                else tf.convert_to_tensor(array)
            )
            result = namespace[framework + "_call"](**{arg: tensor})
            if isinstance(result, torch.Tensor):
                result = result.detach().cpu().numpy()
            elif isinstance(result, tf.Tensor):
                result = result.numpy()
            else:
                raise TypeError("Output is not a framework tensor")
            result = np.asarray(result)
            if not np.isfinite(result).all():
                return {"status": "nonfinite-output"}, None
            return {
                "status": "executed",
                "shape": list(result.shape),
                "dtype": str(result.dtype),
                "values": result.tolist(),
            }, result
        except Exception as error:  # noqa: BLE001 -- retain acquisition/execution failures as evidence
            return {
                "status": "execution-error",
                "type": type(error).__name__,
                "message": str(error)[:1500],
            }, None

    started = time.monotonic()
    source_summary = []
    # A separate complete phase prevents target results from deciding source support.
    for case in cases:
        prop = properties[case["group"]]
        observations = []
        for index, item in enumerate(inputs[case["group"]]):
            array = np.asarray(item["values"], dtype=item["dtype"]).reshape(item["shape"])
            if not valid_input(array, prop["domain"], np):
                raise ValueError("Stored input is outside source domain")
            expected = np.asarray(
                [scalar_reference(case["group"], float(v)) for v in array.flat], dtype="float64"
            ).reshape(array.shape)
            tolerance = prop["reference"][item["dtype"]]
            for repeat in range(3):
                record, actual = invoke(
                    case["source_code"], case["source_framework"], case["argument"], array
                )
                checks = (
                    {}
                    if actual is None
                    else {
                        "shape": actual.shape == array.shape,
                        "dtype": actual.dtype == array.dtype,
                        "value": actual.shape == expected.shape
                        and bool(np.allclose(actual, expected, **tolerance)),
                    }
                )
                observations.append(
                    {
                        "input": index,
                        "repeat": repeat,
                        "output": record,
                        "reference": expected.tolist(),
                        "checks": checks,
                        "supported": bool(checks) and all(checks.values()),
                    }
                )
        save(output / "source" / f"{case['id']}.json", observations)
        source_summary.append(
            {
                "id": case["id"],
                "group": case["group"],
                "supported": all(r["supported"] for r in observations),
                "executions": len(observations),
            }
        )
    save(output / "source-summary.json", source_summary)
    print(
        f"Source phase complete: {sum(s['supported'] for s in source_summary)}/{len(cases)} supported",
        flush=True,
    )

    results = []
    for case in cases:
        sources = json.loads((output / "source" / f"{case['id']}.json").read_text())
        prop = properties[case["group"]]
        observations = []
        for original in sources:
            index, repeat = original["input"], original["repeat"]
            item = inputs[case["group"]][index]
            array = np.asarray(item["values"], dtype=item["dtype"]).reshape(item["shape"])
            record, actual = invoke(
                case["target_code"], case["target_framework"], case["argument"], array
            )
            expected = np.asarray(original["reference"], dtype="float64").reshape(item["shape"])
            tolerance = prop["reference"][item["dtype"]]
            checks = (
                {}
                if actual is None
                else {
                    "shape": actual.shape == array.shape,
                    "dtype": actual.dtype == array.dtype,
                    "value": actual.shape == expected.shape
                    and bool(np.allclose(actual, expected, **tolerance)),
                }
            )
            dllens = None
            if actual is not None and original["output"]["status"] == "executed":
                source_array = np.asarray(
                    original["output"]["values"], dtype=original["output"]["dtype"]
                ).reshape(original["output"]["shape"])
                dllens = bool(compare(source_array, actual))
            observations.append(
                {
                    "input": index,
                    "repeat": repeat,
                    "source_supported": original["supported"],
                    "output": record,
                    "checks": checks,
                    "dllens_outputs_agree": dllens,
                }
            )
        stable = []
        for index in range(len(inputs[case["group"]])):
            runs = [r for r in observations if r["input"] == index]
            if len(runs) == 3 and all(r["source_supported"] and r["checks"] for r in runs):
                failed = [
                    key
                    for key in ["shape", "dtype", "value"]
                    if all(not r["checks"][key] for r in runs)
                ]
                if failed and all(r["output"] == runs[0]["output"] for r in runs):
                    stable.append(
                        {
                            "input": index,
                            "clauses": failed,
                            "dllens_agrees_all_repeats": all(
                                r["dllens_outputs_agree"] is True for r in runs
                            ),
                        }
                    )
        source_ok = all(r["supported"] for r in sources)
        status = (
            "stable-property-violation"
            if source_ok and stable
            else "supported-on-tested-inputs"
            if source_ok and all(r["checks"] and all(r["checks"].values()) for r in observations)
            else "undetermined"
        )
        save(output / "target" / f"{case['id']}.json", observations)
        results.append(
            {
                "id": case["id"],
                "api": case["source_api"],
                "group": case["group"],
                "status": status,
                "source_supported": source_ok,
                "stable_witnesses": stable,
                "target_executions": len(observations),
            }
        )
    save(output / "results.json", results)
    summary = {
        "candidates": len(cases),
        "source_groups": len(properties),
        "source_supported_candidates": sum(r["supported"] for r in source_summary),
        "inputs_per_candidate": 64,
        "repetitions": 3,
        "source_executions": sum(r["executions"] for r in source_summary),
        "target_executions": sum(r["target_executions"] for r in results),
        "statuses": dict(Counter(r["status"] for r in results)),
        "elapsed_seconds": time.monotonic() - started,
        "formal_accuracy_eligible": False,
        "interpretation": "Published counterpart discovery with constructed properties and inputs; finite evidence, not held-out accuracy or new framework bugs.",
    }
    save(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.corpus, args.output)
