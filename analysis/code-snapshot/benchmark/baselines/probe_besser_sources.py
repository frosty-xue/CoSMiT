"""Source-only shape/probability probes for public network class definitions."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from collect_public_corpus import ROOT, save, sha


def worker(corpus: Path, name: str, framework: str) -> dict:
    import numpy as np
    import tensorflow as tf
    import torch

    torch.set_num_threads(1)
    torch.manual_seed(20260916)
    tf.random.set_seed(20260916)
    model = next(
        m for m in json.loads((corpus / "besser-models.json").read_text()) if m["id"] == name
    )
    entry = model["files"][framework]
    path = ROOT / "tmp/baseline-sources/besser-nn-migration" / entry["path"]
    if sha(path.read_bytes()) != entry["sha256"]:
        raise ValueError("Public model file changed")
    namespace = {
        "torch": torch,
        "nn": torch.nn,
        "tf": tf,
        "layers": tf.keras.layers,
        "Sequential": tf.keras.Sequential,
    }
    description = {
        "model": name,
        "framework": framework,
        "source_path": entry["path"],
        "source_sha256": entry["sha256"],
        "scope": "unchanged NeuralNetwork class; source-only inference, no training or weight transfer",
        "seed": 20260916,
        "versions": {
            "torch": torch.__version__,
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
        },
        "clauses": ["batch-and-output-width", "finite-float32"]
        + (
            ["probability-simplex"]
            if name == "lstm"
            else ["unit-interval"]
            if name == "cnn_rnn"
            else []
        ),
        "input_origin": "researcher-constructed from source layer dimensions",
        "observations": [],
    }
    try:
        if framework == "tensorflow" and name in {"alexnet", "vgg16"}:
            import tensorflow_addons as tfa

            namespace["tfa"] = tfa
        exec(compile(entry["class_code"], str(path), "exec"), namespace)  # noqa: S102 -- execute inspected, versioned public code
        network = namespace["NeuralNetwork"]()
        if framework == "pytorch":
            network.eval()
        width = {"alexnet": 1000, "vgg16": 1000, "tf_tutorial": 10, "lstm": 2, "cnn_rnn": 1}[name]
        rng = np.random.default_rng(20260916)
        for batch in [1, 2]:
            if name in {"lstm", "cnn_rnn"}:
                values = rng.integers(
                    0, 10000 if name == "lstm" else 5000, size=(batch, 100), dtype=np.int64
                )
            elif name == "tf_tutorial":
                values = rng.uniform(0, 1, (batch, 32, 32, 3)).astype("float32")
            else:
                shape = (batch, 3, 224, 224) if framework == "pytorch" else (batch, 224, 224, 3)
                values = rng.uniform(0, 1, shape).astype("float32")
            input_record = {
                "shape": list(values.shape),
                "dtype": str(values.dtype),
                "sha256": sha(values.tobytes()),
            }
            for repeat in range(3):
                if framework == "pytorch":
                    with torch.no_grad():
                        actual = network(torch.from_numpy(values.copy())).numpy()
                else:
                    actual = network(tf.convert_to_tensor(values), training=False).numpy()
                checks = {
                    "batch-and-output-width": actual.shape == (batch, width),
                    "finite-float32": str(actual.dtype) == "float32"
                    and bool(np.isfinite(actual).all()),
                }
                if name in {"lstm", "cnn_rnn"}:
                    checks["unit-interval"] = bool(((actual >= 0) & (actual <= 1)).all())
                if name == "lstm":
                    checks["probability-simplex"] = bool(
                        np.allclose(actual.sum(axis=-1), 1, atol=1e-6, rtol=1e-6)
                    )
                description["observations"].append(
                    {
                        "input": input_record,
                        "repeat": repeat,
                        "shape": list(actual.shape),
                        "dtype": str(actual.dtype),
                        "values": actual.tolist(),
                        "checks": checks,
                    }
                )
        description["status"] = (
            "supported-on-tested-inputs"
            if all(all(r["checks"].values()) for r in description["observations"])
            else "source-property-not-supported"
        )
    except Exception as error:  # noqa: BLE001 -- retain acquisition/execution failures as evidence
        description.update(
            status="undetermined",
            error={"type": type(error).__name__, "message": str(error)[:2000]},
        )
    return description


def run(corpus: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "probe_besser_sources.py").write_bytes(Path(__file__).read_bytes())
    models = json.loads((corpus / "besser-models.json").read_text())

    def launch(item: tuple[str, str]) -> dict:
        name, framework = item
        command = [
            sys.executable,
            str(Path(__file__)),
            str(corpus),
            str(output),
            "--worker",
            name,
            framework,
        ]
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "TMPDIR", "SYSTEMROOT"}}
        env.update(TF_CPP_MIN_LOG_LEVEL="2", OMP_NUM_THREADS="1")
        try:
            result = subprocess.run(
                command, env=env, text=True, capture_output=True, timeout=120, check=False
            )
            (output / f"{name}-{framework}.stderr.txt").write_text(result.stderr)
            (output / f"{name}-{framework}.stdout.txt").write_text(result.stdout)
            record = (
                json.loads(result.stdout)
                if result.returncode == 0
                else {
                    "model": name,
                    "framework": framework,
                    "status": "undetermined",
                    "returncode": result.returncode,
                }
            )
        except subprocess.TimeoutExpired:
            record = {
                "model": name,
                "framework": framework,
                "status": "undetermined",
                "error": "timeout-120s",
            }
        save(output / f"{name}-{framework}.json", record)
        print(f"{name} {framework}: {record['status']}", flush=True)
        return record

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(launch, [(m["id"], f) for m in models for f in ["pytorch", "tensorflow"]])
        )
    save(
        output / "summary.json",
        {
            "source_models": len(results),
            "supported": sum(r["status"] == "supported-on-tested-inputs" for r in results),
            "undetermined": sum(r["status"] == "undetermined" for r in results),
            "observed_executions": sum(len(r.get("observations", [])) for r in results),
            "cross_framework_numerical_comparisons": 0,
            "results": [{k: v for k, v in r.items() if k != "observations"} for r in results],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--worker", nargs=2)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.corpus, *args.worker), allow_nan=False))
    else:
        run(args.corpus, args.output)
