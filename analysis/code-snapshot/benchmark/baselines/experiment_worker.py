"""One reviewed candidate per subprocess; records actual calls before verifier decisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from source_property_reference import scalar_reference, valid_input
from verification_ports import ROOT, digest, dllens_comparator, leaves, tensor_shape


def run(case: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import tensorflow as tf
    import torch

    sys.path.insert(0, str(ROOT / "src"))
    from cosmit.engine.certification import Candidate, Observation, Property, evaluate

    expected = digest([case["source"], case["target"]])
    if case.get("reviewed_code_sha256") != expected:
        raise ValueError("candidate code is not the reviewed version")
    domain_id = case["contract"].get("domain_id")
    if domain_id not in {"finite-dense-floats-v1", "bounded-unary-v1"}:
        raise ValueError("unregistered input domain")
    compare = dllens_comparator(np)
    records = []

    def observe(spec: dict[str, Any], arguments: dict[str, Any], target: bool) -> dict[str, Any]:
        env = {"np": np, "tf": tf, "torch": torch}
        args = {}
        calls = []
        owner, attribute, original = None, None, None
        started = time.perf_counter()
        try:
            for name, arg in arguments.items():
                value = arg.get("values", arg.get("value"))
                if arg["kind"] == "tensor":
                    raw = np.asarray(value, dtype=arg["dtype"])
                    args[name] = (
                        torch.tensor(raw) if spec["framework"] == "pytorch" else tf.constant(raw)
                    )
                else:
                    args[name] = value
            if target:
                parts = spec["api"].split(".")
                owner = env[parts[0]]
                for part in parts[1:-1]:
                    owner = getattr(owner, part)
                attribute = parts[-1]
                original = getattr(owner, attribute)

                def wrapped(*args: Any, **kwargs: Any) -> Any:
                    calls.append(spec["api"])
                    return original(*args, **kwargs)

                setattr(owner, attribute, wrapped)
            exec(spec["code"], env)  # noqa: S102 -- parent verifies reviewed candidate hash; bounded subprocess
            value = env[spec["entry"]](**args)
            array = np.asarray(value.detach().numpy() if isinstance(value, torch.Tensor) else value)
            if array.dtype.kind not in "bifu" or not np.all(np.isfinite(array)):
                return {"status": "unsupported-output", "calls": calls}
            return {
                "status": "ok",
                "value": array.tolist(),
                "dtype": str(array.dtype),
                "shape": list(array.shape),
                "calls": calls,
                "seconds": time.perf_counter() - started,
            }
        except Exception as exc:  # noqa: BLE001 -- record every candidate/framework failure
            return {
                "status": "error",
                "error": type(exc).__name__,
                "message": str(exc)[:1000],
                "calls": calls,
                "seconds": time.perf_counter() - started,
            }
        finally:
            if original is not None:
                setattr(owner, attribute, original)

    for index, arguments in enumerate(case["inputs"]):
        valid = all(
            arg["kind"] == "tensor"
            and arg["dtype"] in {"float32", "float64"}
            and len(tensor_shape(arg["values"])) <= 4
            and len(leaves(arg["values"])) <= 4096
            and all(type(v) in {int, float} and np.isfinite(v) for v in leaves(arg["values"]))
            for arg in arguments.values()
        )
        if not valid:
            records.append({"input_index": index, "status": "invalid-input", "repeat": 0})
            continue
        if domain_id == "bounded-unary-v1":
            valid = len(arguments) == 1 and all(
                valid_input(
                    np.asarray(arg["values"], dtype=arg["dtype"]),
                    case["contract"]["registered_domain"],
                    np,
                )
                for arg in arguments.values()
            )
            if not valid:
                records.append({"input_index": index, "status": "invalid-input", "repeat": 0})
                continue
        for repeat in range(3):
            np.random.seed(20260916 + index)
            torch.manual_seed(20260916 + index)
            tf.random.set_seed(20260916 + index)
            src = observe(case["source"], arguments, False)
            dst = observe(case["target"], arguments, True)
            row = {"input_index": index, "repeat": repeat, "source": src, "target": dst}
            source_valid = True
            tolerance = {k: case["contract"][k] for k in ["atol", "rtol"]}
            if domain_id == "bounded-unary-v1" and src["status"] == "ok":
                arg = next(iter(arguments.values()))
                raw = np.asarray(arg["values"], dtype=arg["dtype"])
                reference = np.asarray(
                    [scalar_reference(case["contract"]["family"], float(v)) for v in raw.flat]
                ).reshape(raw.shape)
                tolerance = case["contract"]["tolerance_by_dtype"][arg["dtype"]]
                source_valid = (
                    src["shape"] == list(raw.shape)
                    and src["dtype"] == str(raw.dtype)
                    and bool(np.allclose(np.asarray(src["value"]), reference, **tolerance))
                )
                row["source_reference_supported"] = source_valid
            if src["status"] != "ok":
                row["status"] = (
                    "invalid-source-test"
                    if src.get("error") == "AssertionError"
                    else "undetermined"
                )
            elif not source_valid:
                row["status"] = "invalid-source-assumption"
            elif dst["status"] != "ok":
                row["status"] = "undetermined"
            else:
                row["status"] = "executed"
                row["dllens_agrees"] = bool(
                    compare(
                        np.asarray(src["value"], dtype=src["dtype"]),
                        np.asarray(dst["value"], dtype=dst["dtype"]),
                    )
                )
                row["clause_results"] = []

                def observation(record: dict[str, Any]) -> Observation:
                    return Observation(
                        value=record["value"], shape=tuple(record["shape"]), dtype=record["dtype"]
                    )

                for clause in case["contract"]["clauses"]:
                    prop = Property(
                        case["id"],
                        clause,
                        clause,
                        lambda _: True,
                        lambda _, src=src: observation(src),
                        tolerance["atol"],
                        tolerance["rtol"],
                    )
                    candidate = Candidate(
                        case["id"],
                        lambda _, dst=dst: observation(dst),
                        case["origin"],
                        expected,
                        "registered-target-operation" if dst["calls"] else "unverified",
                    )
                    row["clause_results"].append(evaluate(prop, candidate, {"input_index": index}))
            records.append(row)
    return {
        "case_id": case["id"],
        "status": "completed",
        "records": records,
        "versions": {
            "tensorflow": tf.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "paired_executions": sum("source" in r for r in records),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    result = run(json.loads(args.case.read_text()))
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
