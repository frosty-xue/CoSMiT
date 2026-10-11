"""Replay original trunc inputs and weight-aligned public network pairs."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from collect_public_corpus import ROOT, save, sha
from verification_ports import dllens_comparator, upstream


def run(corpus: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import tensorflow as tf
    import torch

    torch.set_num_threads(1)
    torch.manual_seed(20260916)
    np.random.seed(20260916)
    tf.random.set_seed(20260916)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(
        output / "configuration.json",
        {
            "torch": torch.__version__,
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
            "seed": 20260916,
            "atol": 1e-6,
            "rtol": 1e-5,
            "purpose": "discovery validation, not held-out evaluation",
            "implementation_sha256": sha(Path(__file__).read_bytes()),
        },
    )
    namespace = {"np": np, "torch": torch, "tf": tf, "nn": torch.nn}
    original = json.loads(
        upstream("dllens", "data/working_dir/rq1/dllens/pytorch/counterparts/torch.trunc.json")
    )
    for code in original["counterparts"].values():
        exec(compile(code, "frozen-trunc", "exec"), namespace)  # noqa: S102 -- execute inspected, versioned public code
    compare = dllens_comparator(np)
    regression = []
    for index, code in enumerate(original["sample_inputs"]):
        exec(compile(code, "public-trunc-input", "exec"), namespace)  # noqa: S102 -- execute inspected, versioned public code
        tensor = namespace["input"]
        values = tensor.numpy()
        for repeat in range(3):
            source = namespace["pytorch_call"](tensor).numpy()
            target = namespace["tensorflow_call"](tf.convert_to_tensor(values)).numpy()
            regression.append(
                {
                    "input": index,
                    "repeat": repeat,
                    "input_code": code,
                    "values": values.tolist(),
                    "dtype": str(values.dtype),
                    "source": source.tolist(),
                    "target": target.tolist(),
                    "dllens_agrees": bool(compare(source, target)),
                    "exact_value_agrees": bool(np.array_equal(source, target)),
                }
            )
    save(output / "trunc-original-inputs.json", regression)

    # Fixed public weight-copy helpers, validated against the new source lock.
    root = ROOT / "tmp/baseline-sources/besser-nn-migration"
    relative = "EXP_random_inputs/test_functional_behavior.py"
    source = root / relative
    lock = next(
        r
        for r in json.loads((corpus / "sources.lock.json").read_text())
        if r["name"] == "besser-nn-migration"
    )
    if sha(source.read_bytes()) != next(
        r["sha256"] for r in lock["files"] if r["path"] == relative
    ):
        raise ValueError("Weight-copy helper differs from frozen source")
    nodes = [
        n
        for n in ast.parse(source.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name.startswith("copy_")
    ]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "frozen-weight-copy", "exec"), namespace)  # noqa: S102 -- execute inspected, versioned public code
    pairs = []
    models = json.loads((corpus / "besser-models.json").read_text())
    for name in ["tf_tutorial", "lstm"]:
        record = {
            "model": name,
            "kind": "public-paired-network-definitions",
            "observations": [],
            "weight_alignment": "public copy_model_weights: PyTorch to TensorFlow",
            "layout": "same NHWC for tf_tutorial; same token indices for lstm",
            "clauses": ["source-supported-shape", "aligned-weight-output-values"],
            "status": "undetermined",
        }
        try:
            networks = {}
            model = next(m for m in models if m["id"] == name)
            for framework in ["pytorch", "tensorflow"]:
                env = {**namespace, "layers": tf.keras.layers, "Sequential": tf.keras.Sequential}
                entry = model["files"][framework]
                if sha((root / entry["path"]).read_bytes()) != entry["sha256"]:
                    raise ValueError("Public model changed")
                exec(compile(entry["class_code"], entry["path"], "exec"), env)  # noqa: S102 -- execute inspected, versioned public code
                networks[framework] = env["NeuralNetwork"]()
            pt_model, tf_model = networks["pytorch"], networks["tensorflow"]
            pt_model.eval()
            # Build and align once; inference reuses the same frozen weights.
            rng = np.random.default_rng(20260916)
            sample = (
                torch.zeros((1, 32, 32, 3))
                if name == "tf_tutorial"
                else torch.zeros((1, 100), dtype=torch.int64)
            )
            namespace["copy_model_weights"](tf_model, pt_model, sample)
            record["pt_state_sha256"] = sha(
                b"".join(v.detach().numpy().tobytes() for v in pt_model.state_dict().values())
            )
            for batch in [1, 2]:
                values = (
                    rng.uniform(0, 1, (batch, 32, 32, 3)).astype("float32")
                    if name == "tf_tutorial"
                    else rng.integers(0, 10000, (batch, 100), dtype=np.int64)
                )
                for repeat in range(3):
                    with torch.no_grad():
                        pt_out = pt_model(torch.from_numpy(values.copy())).numpy()
                    tf_out = tf_model(tf.convert_to_tensor(values), training=False).numpy()
                    same_shape = pt_out.shape == tf_out.shape
                    record["observations"].append(
                        {
                            "batch": batch,
                            "repeat": repeat,
                            "input_sha256": sha(values.tobytes()),
                            "source_values": pt_out.tolist(),
                            "target_values": tf_out.tolist(),
                            "same_shape": same_shape,
                            "close": same_shape
                            and bool(np.allclose(pt_out, tf_out, atol=1e-6, rtol=1e-5)),
                            "max_absolute_difference": float(np.max(np.abs(pt_out - tf_out)))
                            if same_shape
                            else None,
                        }
                    )
            record["status"] = (
                "supported-on-tested-inputs"
                if all(r["close"] for r in record["observations"])
                else "observed-difference-needs-attribution"
            )
        except Exception as error:  # noqa: BLE001 -- retain acquisition/execution failures as evidence
            record["error"] = {"type": type(error).__name__, "message": str(error)[:2000]}
        pairs.append(record)
        save(output / f"{name}-aligned.json", record)
    save(
        output / "summary.json",
        {
            "trunc_public_inputs": len(original["sample_inputs"]),
            "trunc_pair_executions": len(regression),
            "trunc_original_disagreements": sum(not r["dllens_agrees"] for r in regression),
            "network_pairs": [
                {
                    "model": r["model"],
                    "status": r["status"],
                    "pair_executions": len(r["observations"]),
                    "error": r.get("error"),
                }
                for r in pairs
            ],
        },
    )
    print((output / "summary.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.corpus, args.output)
