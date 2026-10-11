"""Isolated compatibility probes and unchanged TensorScope converter execution."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from collect_public_corpus import ROOT, save, sha


def run(output: Path) -> None:
    output = output.resolve()
    with (output / "execution.lock").open("x") as stream:
        stream.write(str(os.getpid()))
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    corpus = ROOT / "artifacts/dataset-sources/20260916-v1"
    # Do not import frameworks into the subprocess controller before source probes.
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "TMPDIR"}}
    env.update(
        PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""),
        TF_CPP_MIN_LOG_LEVEL="2",
        OMP_NUM_THREADS="1",
    )
    with (output / "besser.log").open("w") as log:
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "benchmark/baselines/probe_besser_sources.py"),
                str(corpus),
                str(output / "besser-source-execution"),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=900,
            check=False,
        )
    save(output / "besser-controller.json", {"exit_code": process.returncode})

    directory = output / "tensorscope"
    directory.mkdir()
    source = ROOT / "tmp/baseline-sources/tensorscope/src/testing/tf2torch_op_test.py"
    lock = next(
        r
        for r in json.loads((corpus / "sources.lock.json").read_text())
        if r["name"] == "tensorscope"
    )
    expected = next(
        r["sha256"] for r in lock["files"] if r["path"] == "src/testing/tf2torch_op_test.py"
    )
    if sha(source.read_bytes()) != expected:
        raise ValueError("Frozen TensorScope code changed")
    (directory / "original-script.py").write_bytes(source.read_bytes())
    with (directory / "original-script.log").open("w") as log:
        process = subprocess.run(
            [sys.executable, str(source)],
            cwd=directory,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=240,
            check=False,
        )
    save(
        directory / "original-execution.json",
        {
            "exit_code": process.returncode,
            "source_sha256": expected,
            "command": [sys.executable, str(source)],
            "original_source_unchanged": True,
        },
    )

    import numpy as np
    import tensorflow as tf
    import torch

    torch.set_num_threads(1)
    # Source CNN-RNN shape check: no edits or repairs to the public network.
    source = (
        ROOT / "tmp/baseline-sources/besser-nn-migration/output/cnn_rnn/pytorch_nn_subclassing.py"
    )
    code = source.read_text()
    node = next(
        n for n in ast.parse(code).body if isinstance(n, ast.ClassDef) and n.name == "NeuralNetwork"
    )
    namespace = {"torch": torch, "nn": torch.nn}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)  # noqa: S102 -- inspected public class
    model = namespace["NeuralNetwork"]().eval()
    records = []
    for length in [49, 50, 51, 100]:
        for repeat in range(3):
            try:
                value = model(torch.zeros((1, length), dtype=torch.int64))
                records.append(
                    {
                        "length": length,
                        "repeat": repeat,
                        "status": "executed",
                        "shape": list(value.shape),
                    }
                )
            except Exception as error:  # noqa: BLE001 -- preserve source failures
                records.append(
                    {
                        "length": length,
                        "repeat": repeat,
                        "status": "source-execution-error",
                        "error": type(error).__name__,
                        "message": str(error),
                    }
                )
    save(
        output / "cnn-rnn-source-diagnosis.json",
        {
            "source_sha256": sha(source.read_bytes()),
            "declared_input": "rank-2 integer token array [batch, length], indices in [0,4999]",
            "shape_derivation": [
                "Embedding gives [B,L,50].",
                "Conv1d(in_channels=50) on this unchanged layout requires L=50.",
                "At L=50, last dimension 50 becomes floor((50-4+1)/2)=23 and floor((50-5+1)/2)=23 in the two branches.",
                "Concatenating the unchanged last axis gives [B,200,46].",
                "GRU requires last dimension 400; 46 != 400.",
            ],
            "status": "source-contract-not-executable-for-declared-rank2-token-domain",
            "target_bug_claim": False,
            "records": records,
        },
    )
    summary = {
        "tensorflow": tf.__version__,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "tensorscope_original_exit": process.returncode,
    }
    if process.returncode == 0:
        import onnx
        import onnxruntime as ort
        from onnx2torch import convert

        onnx_path = directory / "models/tf2pytorch/model.onnx"
        onnx.checker.check_model(onnx.load(onnx_path))
        tf_model = tf.saved_model.load(str(directory / "models/tf2pytorch"))
        torch_model = convert(str(onnx_path)).eval()
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        rng = np.random.default_rng(20260916)
        values = [-2147483647, -100, -1, 0, 1, 100, 2147483647] + rng.integers(
            -10000, 10001, size=57
        ).tolist()
        save(
            directory / "property-and-inputs.json",
            {
                "property": "int32 absolute value, shape [1], dtype int32",
                "domain": [-2147483647, 2147483647],
                "excluded": "int32 minimum excluded to avoid nonrepresentable positive absolute value",
                "source_reference": "Python integer abs on typed source input",
                "values": values,
                "repetitions": 3,
                "partition": "previously-exposed-abs; new converter/source provenance only",
            },
        )
        records = []
        for index, value in enumerate(values):
            array = np.asarray([value], dtype=np.int32)
            for repeat in range(3):
                a = tf_model(tf.constant(array)).numpy()
                b = session.run(None, {session.get_inputs()[0].name: array})[0]
                with torch.no_grad():
                    c = torch_model(torch.from_numpy(array.copy())).numpy()
                reference = np.asarray([abs(int(array[0]))], dtype=np.int32)
                checks = {
                    name: actual.shape == (1,)
                    and actual.dtype == np.int32
                    and bool(np.array_equal(actual, reference))
                    for name, actual in [("source", a), ("onnxruntime", b), ("torch", c)]
                }
                records.append(
                    {
                        "input": index,
                        "repeat": repeat,
                        "value": value,
                        "source": a.tolist(),
                        "onnx": b.tolist(),
                        "torch": c.tolist(),
                        "checks": checks,
                    }
                )
        save(
            directory / "validation.json",
            {
                "records": records,
                "triplet_executions": len(records),
                "all_passed": all(all(r["checks"].values()) for r in records),
                "onnx_sha256": sha(onnx_path.read_bytes()),
            },
        )
        summary["tensorscope_validation"] = (
            "supported-on-tested-inputs"
            if all(all(r["checks"].values()) for r in records)
            else "observed-difference"
        )
    save(output / "summary.json", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
