"""Execute the pre-frozen six-family domain using unchanged common verifier rules."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from unseen_properties import reference, valid_domain
from verification_ports import ROOT, digest, dllens_comparator


def run(case: dict) -> dict:
    import numpy as np
    import tensorflow as tf
    import torch

    torch.set_num_threads(1)
    sys.path.insert(0, str(ROOT / "src"))
    from cosmit.engine.certification import Candidate, Observation, Property, evaluate

    if (
        case["contract"]["domain_id"] != "reserved-matrix-ops-v1"
        or digest([case["source"], case["target"]]) != case["reviewed_code_sha256"]
    ):
        raise ValueError("Unregistered domain or modified public code")
    compare = dllens_comparator(np)
    family = case["group"]

    def observe(spec: dict, arguments: dict, target: bool) -> dict:
        environment = {"tf": tf, "torch": torch, "np": np}
        calls, patches = [], []
        started = time.perf_counter()
        try:
            values = {
                name: (
                    torch.tensor(np.asarray(arg["values"], dtype=arg["dtype"]))
                    if spec["framework"] == "pytorch"
                    else tf.constant(np.asarray(arg["values"], dtype=arg["dtype"]))
                )
                if arg["kind"] == "tensor"
                else arg["value"]
                for name, arg in arguments.items()
            }
            if target:
                for api in spec["apis"]:
                    parts = api.split(".")
                    owner = environment[parts[0]]
                    for part in parts[1:-1]:
                        owner = getattr(owner, part)
                    attribute = parts[-1]
                    original = getattr(owner, attribute)

                    def wrapper(
                        *args: Any, _api: str = api, _original: Any = original, **kwargs: Any
                    ) -> Any:
                        calls.append(_api)
                        return _original(*args, **kwargs)

                    patches.append((owner, attribute, original))
                    setattr(owner, attribute, wrapper)
            exec(spec["code"], environment)  # noqa: S102 -- frozen, inspected public functions
            result = environment[spec["entry"]](**values)
            if not isinstance(result, (tf.Tensor, torch.Tensor)):
                raise TypeError("Output is not a framework tensor")
            array = result.detach().numpy() if isinstance(result, torch.Tensor) else result.numpy()
            if not np.isfinite(array).all():
                return {"status": "unsupported-output", "calls": calls}
            return {
                "status": "ok",
                "value": array.tolist(),
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "calls": calls,
                "seconds": time.perf_counter() - started,
            }
        except Exception as error:  # noqa: BLE001 -- retain all framework/candidate failures
            return {
                "status": "error",
                "error": type(error).__name__,
                "message": str(error)[:1500],
                "calls": calls,
                "seconds": time.perf_counter() - started,
            }
        finally:
            for owner, attribute, original in reversed(patches):
                setattr(owner, attribute, original)

    records = []
    names = case["argument_names"]
    for index, arguments in enumerate(case["inputs"]):
        matrix = np.asarray(arguments[names[0]]["values"], dtype=arguments[names[0]]["dtype"])
        other = (
            np.asarray(arguments[names[1]]["values"], dtype=arguments[names[1]]["dtype"])
            if family == "matmul"
            else None
        )
        axis = arguments[names[1]]["value"] if family in {"prod", "cumsum", "cumprod"} else 0
        keepdim = arguments[names[2]]["value"] if family == "prod" else False
        literal_valid = type(keepdim) is bool
        if family == "matmul":
            literal_valid &= all(
                arguments[name]["value"] is (None if name == "output_type" else False)
                for name in names[2:]
            )
        if family in {"cumsum", "cumprod"}:
            literal_valid &= all(arguments[name]["value"] is False for name in names[2:])
        if not literal_valid or not valid_domain(family, matrix, other, axis, np):
            records.append({"input_index": index, "repeat": 0, "status": "invalid-input"})
            continue
        expected = reference(family, matrix, other, axis, keepdim, np)
        tolerance = case["contract"]["tolerance_by_dtype"][str(matrix.dtype)]
        for repeat in range(3):
            source = observe(case["source"], arguments, False)
            target = observe(case["target"], arguments, True)
            row = {"input_index": index, "repeat": repeat, "source": source, "target": target}
            valid_source = (
                source["status"] == "ok"
                and source["shape"] == list(expected.shape)
                and source["dtype"] == str(matrix.dtype)
                and bool(np.allclose(np.asarray(source["value"]), expected, **tolerance))
            )
            row["source_reference_supported"] = valid_source
            if source["status"] != "ok":
                row["status"] = (
                    "invalid-source-test"
                    if source.get("error") == "AssertionError"
                    else "undetermined"
                )
            elif not valid_source:
                row["status"] = "invalid-source-assumption"
            elif target["status"] != "ok":
                row["status"] = "undetermined"
            else:
                row["status"] = "executed"
                row["dllens_agrees"] = bool(
                    compare(
                        np.asarray(source["value"], dtype=source["dtype"]),
                        np.asarray(target["value"], dtype=target["dtype"]),
                    )
                )
                row["clause_results"] = []

                def observation(record: dict) -> Observation:
                    return Observation(
                        value=record["value"], dtype=record["dtype"], shape=tuple(record["shape"])
                    )

                for clause in case["contract"]["clauses"]:
                    prop = Property(
                        case["id"],
                        clause,
                        clause,
                        lambda _: True,
                        lambda _, source=source: observation(source),
                        tolerance["atol"],
                        tolerance["rtol"],
                    )
                    candidate = Candidate(
                        case["id"],
                        lambda _, target=target: observation(target),
                        case["origin"],
                        case["reviewed_code_sha256"],
                        "registered-target-operation" if target["calls"] else "unverified",
                    )
                    row["clause_results"].append(evaluate(prop, candidate, {"input_index": index}))
            records.append(row)
    return {
        "case_id": case["id"],
        "status": "completed",
        "records": records,
        "paired_executions": sum("source" in r for r in records),
        "versions": {
            "tensorflow": tf.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    result = run(json.loads(args.case.read_text()))
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
