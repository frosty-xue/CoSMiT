"""Validate original AlexNet/VGG definitions with explicit weight/layout alignment."""

from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from collect_public_corpus import ROOT, save, sha


def aligned_dense_kernel(weight: Any, channels: int, height: int, width: int) -> Any:
    if weight.ndim != 2 or weight.shape[1] != channels * height * width:
        raise ValueError("Dense input width does not match the source feature geometry")
    return (
        weight.reshape(weight.shape[0], channels, height, width)
        .transpose(2, 3, 1, 0)
        .reshape(height * width * channels, weight.shape[0])
    )


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import tensorflow as tf
    import tensorflow_addons as tfa
    import torch

    torch.set_num_threads(1)
    corpus = ROOT / "artifacts/dataset-sources/20260916-v1"
    root = ROOT / "tmp/baseline-sources/besser-nn-migration"
    models = json.loads((corpus / "besser-models.json").read_text())
    lock = next(
        r
        for r in json.loads((corpus / "sources.lock.json").read_text())
        if r["name"] == "besser-nn-migration"
    )
    helper_path = "EXP_random_inputs/test_functional_behavior.py"
    helper = root / helper_path
    if sha(helper.read_bytes()) != next(
        r["sha256"] for r in lock["files"] if r["path"] == helper_path
    ):
        raise ValueError("Public weight-copy functions changed")
    namespace = {
        "np": np,
        "torch": torch,
        "nn": torch.nn,
        "tf": tf,
        "tfa": tfa,
        "layers": tf.keras.layers,
        "Sequential": tf.keras.Sequential,
    }
    nodes = [
        n
        for n in ast.parse(helper.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name.startswith("copy_")
    ]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), helper_path, "exec"), namespace)  # noqa: S102 -- frozen public weight-copy functions
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(
        output / "protocol.json",
        {
            "models": ["alexnet", "vgg16"],
            "seed": 20260916,
            "input": "canonical NHWC float32 values [0,1]; explicit NCHW transpose for PyTorch",
            "weight_alignment": "public convolution/dense weight transfer, followed by first classifier kernel CHW-to-HWC input-index permutation",
            "dtype": "float32",
            "atol": 1e-6,
            "rtol": 1e-5,
            "batches": [1, 2],
            "repetitions": 3,
            "source_classes_modified": False,
            "scope": "inference of paired definitions with corresponding weights; not training or migration-generation evaluation",
            "versions": {
                "tensorflow": tf.__version__,
                "torch": torch.__version__,
                "numpy": np.__version__,
                "tensorflow_addons": tfa.__version__,
            },
        },
    )
    results = []
    for name in ["alexnet", "vgg16"]:
        record = {
            "model": name,
            "status": "undetermined",
            "observations": [],
            "setup_target_forward_calls": 0,
            "setup_source_partial_feature_calls": 0,
        }
        try:
            torch.manual_seed(20260916)
            tf.random.set_seed(20260916)
            definition = next(m for m in models if m["id"] == name)
            networks = {}
            for framework in ["pytorch", "tensorflow"]:
                entry = definition["files"][framework]
                if sha((root / entry["path"]).read_bytes()) != entry["sha256"]:
                    raise ValueError("Frozen model code changed")
                env = namespace.copy()
                exec(compile(entry["class_code"], entry["path"], "exec"), env)  # noqa: S102 -- unchanged public model class
                networks[framework] = env["NeuralNetwork"]()
            pt_model, tf_model = networks["pytorch"], networks["tensorflow"]
            pt_model.eval()
            namespace["copy_model_weights"](tf_model, pt_model, torch.zeros((1, 224, 224, 3)))
            record["setup_target_forward_calls"] += 1
            with torch.no_grad():
                features = pt_model.p1(pt_model.features(torch.zeros((1, 3, 224, 224))))
            record["setup_source_partial_feature_calls"] += 1
            _, channels, height, width = features.shape
            pt_first = next(
                m for m in pt_model.classifier.modules() if isinstance(m, torch.nn.Linear)
            )
            tf_first = next(
                m for m in tf_model.classifier.layers if isinstance(m, tf.keras.layers.Dense)
            )
            kernel = aligned_dense_kernel(pt_first.weight.detach().numpy(), channels, height, width)
            tf_first.set_weights([kernel, pt_first.bias.detach().numpy()])
            record["source_feature_geometry"] = [channels, height, width]
            record["aligned_first_dense_kernel_sha256"] = sha(kernel.tobytes())
            state_hash = hashlib.sha256()
            for value in pt_model.state_dict().values():
                state_hash.update(value.detach().numpy().tobytes())
            record["source_state_sha256"] = state_hash.hexdigest()
            rng = np.random.default_rng(20260916)
            for batch in [1, 2]:
                values = rng.uniform(0, 1, (batch, 224, 224, 3)).astype("float32")
                for repeat in range(3):
                    with torch.no_grad():
                        source = pt_model(
                            torch.from_numpy(values.transpose(0, 3, 1, 2).copy())
                        ).numpy()
                    target = tf_model(tf.constant(values), training=False).numpy()
                    checks = {
                        "shape": source.shape == target.shape == (batch, 1000),
                        "dtype": str(source.dtype) == str(target.dtype) == "float32",
                        "finite": bool(np.isfinite(source).all() and np.isfinite(target).all()),
                        "value": source.shape == target.shape
                        and bool(np.allclose(source, target, atol=1e-6, rtol=1e-5)),
                    }
                    record["observations"].append(
                        {
                            "batch": batch,
                            "repeat": repeat,
                            "input_sha256": sha(values.tobytes()),
                            "source": source.tolist(),
                            "target": target.tolist(),
                            "checks": checks,
                            "max_absolute_difference": float(np.max(np.abs(source - target)))
                            if source.shape == target.shape
                            else None,
                        }
                    )
            record["status"] = (
                "supported-on-tested-inputs"
                if all(all(r["checks"].values()) for r in record["observations"])
                else "observed-difference-needs-attribution"
            )
            del networks, pt_model, tf_model, pt_first, tf_first, kernel, features, source, target
        except Exception as error:  # noqa: BLE001 -- preserve all model/alignment failures
            record["error"] = {"type": type(error).__name__, "message": str(error)[:2000]}
        save(output / (name + ".json"), record)
        print(name, record["status"], flush=True)
        results.append({k: v for k, v in record.items() if k != "observations"})
        tf.keras.backend.clear_session()
        gc.collect()
    save(
        output / "summary.json",
        {
            "results": results,
            "pair_executions": sum(
                len(json.loads((output / (r["model"] + ".json")).read_text())["observations"])
                for r in results
            ),
            "weight_alignment_is_assumption": True,
            "public_source_classes_changed": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
