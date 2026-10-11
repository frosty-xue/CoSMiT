"""Local component replay of two reviewed DLLens pairs; NOT the original pipeline.

Execute original counterpart bodies and comparator functions unchanged. The adapter
converts one concrete source tensor to the target framework via NumPy so both sides
receive the same values. No LLM generation, upstream mutation or constraint solving.
Only the two explicitly reviewed abs artifacts may be executed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "tmp/baseline-sources/dllens"
SELECTED = ["pytorch/counterparts/torch.Tensor.abs.json", "tensorflow/counterparts/tf.abs.json"]


def smoke(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    import numpy as np
    import tensorflow as tf
    import torch

    manifest = json.loads(
        (ROOT / "artifacts/baselines/20260916-v1/sources/sources.lock.json").read_text()
    )
    locked = next(r for r in manifest["sources"] if r["name"] == "dllens")
    hashes = {r["path"]: r["sha256"] for r in locked["files"]}

    def read_verified(relative: str) -> str:
        data = (UPSTREAM / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != hashes[relative]:
            raise ValueError(f"upstream source changed: {relative}")
        return data.decode()

    comparator_path = "codes/counterpart/evaluate_counterpart.py"
    tree = ast.parse(read_verified(comparator_path))
    names = {"compare_res", "convert_to_numpy", "sparse_to_dense"}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(functions) != len(names):
        raise ValueError("missing original comparator function")
    namespace = {"np": np}
    # Execute only reviewed, hash-verified upstream comparator definitions.
    exec(compile(ast.Module(body=functions, type_ignores=[]), comparator_path, "exec"), namespace)  # noqa: S102
    compare = namespace["compare_res"]
    rows = []
    for selected in SELECTED:
        relative = "data/working_dir/rq1/dllens/" + selected
        candidate = json.loads(read_verified(relative))
        source = selected.split("/")[0]
        target = "tensorflow" if source == "pytorch" else "pytorch"
        arg = candidate["inputs"][0]
        for index, input_code in enumerate(candidate["sample_inputs"]):
            row = {"candidate": selected, "input_index": index, "seed": 20260916 + index}
            try:
                np.random.seed(row["seed"])
                torch.manual_seed(row["seed"])
                tf.random.set_seed(row["seed"])
                env = {"np": np, "tf": tf, "torch": torch}
                exec(input_code, env)  # noqa: S102 -- two reviewed, hash-verified abs records only
                source_input = env[arg]
                raw = source_input.numpy().copy()
                target_input = tf.constant(raw) if target == "tensorflow" else torch.tensor(raw)
                for code in candidate["counterparts"].values():
                    exec(code, env)  # noqa: S102 -- unchanged, hash-verified counterpart bodies
                src_output = env[source + "_call"](source_input)
                dst_output = env[target + "_call"](target_input)
                src, dst = src_output.numpy(), dst_output.numpy()
                row.update(
                    {
                        "status": "executed",
                        "input_shape": list(raw.shape),
                        "input_dtype": str(raw.dtype),
                        "input_values": raw.tolist(),
                        "source_output": src.tolist(),
                        "target_output": dst.tolist(),
                        "dllens_comparator_agrees": bool(compare(src_output, dst_output)),
                        "exact_shape_dtype_value_agrees": bool(
                            src.shape == dst.shape
                            and src.dtype == dst.dtype
                            and np.array_equal(src, dst)
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001 -- retain each framework execution failure
                row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
            rows.append(row)
    controls = []
    for name, left, right, expected in [
        ("identical", [1.0, 2.0], [1.0, 2.0], True),
        ("large_difference", [1.0, 2.0], [1.0, 4.0], False),
        ("original_loose_tolerance", [1.0], [1.05], True),
        ("original_shape_flattening", [[1.0, 2.0]], [[1.0], [2.0]], True),
    ]:
        actual = bool(compare(np.array(left), np.array(right)))
        controls.append(
            {
                "name": name,
                "expected_upstream_result": expected,
                "actual": actual,
                "pass": actual == expected,
            }
        )
    result = {
        "classification": "adapted-component-smoke-not-full-reproduction",
        "python": sys.version,
        "platform": platform.platform(),
        "versions": {p: importlib.metadata.version(p) for p in ["torch", "tensorflow", "numpy"]},
        "upstream_commit": locked["commit"],
        "candidate_count": len(SELECTED),
        "records": rows,
        "comparator_controls": controls,
    }
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "pairs": len(rows),
                "executed": sum(r["status"] == "executed" for r in rows),
                "comparator_agrees": sum(r.get("dllens_comparator_agrees", False) for r in rows),
                "control_checks_pass": all(r["pass"] for r in controls),
            }
        )
    )
    if any(r["status"] != "executed" for r in rows) or not all(r["pass"] for r in controls):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    smoke(parser.parse_args().output)
