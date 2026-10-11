"""Freeze public materials and source-derived contracts before executing targets."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

from verification_ports import ROOT, upstream

FAMILIES = [
    "abs",
    "neg",
    "square",
    "sqrt",
    "exp",
    "log",
    "sin",
    "cos",
    "tanh",
    "ceil",
    "floor",
    "trunc",
    "round",
    "sign",
    "reciprocal",
    "sigmoid",
    "sinh",
    "cosh",
    "tan",
    "asin",
    "acos",
    "atan",
    "expm1",
    "log1p",
]
ALIASES = {
    "negative": "neg",
    "arcsin": "asin",
    "arccos": "acos",
    "arctan": "atan",
    "absolute": "abs",
}
PINS = {
    "tensorscope": "8015abe2340f2666242b07bd156ed533baf971bd",
    "besser-nn-migration": "4cd3e0b826989140c74bf64c3c929a2f48fea346",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def bounds(family: str) -> tuple[float, float]:
    if family in {"asin", "acos"}:
        return -1.0, 1.0
    if family == "sqrt":
        return 0.0, 8.0
    if family in {"log", "reciprocal"}:
        return 2**-10, 8.0
    if family == "log1p":
        return -0.5, 8.0
    if family == "tan":
        return -1.4, 1.4
    return -8.0, 8.0


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def collect(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    sources = []
    for name, commit in PINS.items():
        repo = ROOT / "tmp/baseline-sources" / name
        if (
            git(repo, "rev-parse", "HEAD").decode().strip() != commit
            or git(repo, "status", "--porcelain").strip()
        ):
            raise ValueError(f"Unpinned or dirty source: {name}")
        paths = git(repo, "ls-files", "-z").decode().strip("\0").split("\0")
        files = [{"path": p, "sha256": sha((repo / p).read_bytes())} for p in paths]
        archive = gzip.compress(git(repo, "archive", "HEAD"), mtime=0)
        archive_path = output / f"{name}.tar.gz"
        archive_path.write_bytes(archive)
        sources.append(
            {
                "name": name,
                "commit": commit,
                "url": git(repo, "remote", "get-url", "origin").decode().strip(),
                "files": files,
                "archive": archive_path.name,
                "archive_sha256": sha(archive),
            }
        )
    save(output / "sources.lock.json", sources)

    # Save versioned documentation, including raw op specifications for TF.
    specs = {
        "torch-docs.py": "https://raw.githubusercontent.com/pytorch/pytorch/v2.1.0/torch/_torch_docs.py"
    }
    for family in FAMILIES:
        if family != "trunc":
            op = {"neg": "Neg", "ceil": "Ceil"}.get(family, family.capitalize())
            specs[f"tf-{family}.pbtxt"] = (
                f"https://raw.githubusercontent.com/tensorflow/tensorflow/v2.16.2/tensorflow/core/api_def/base_api/api_def_{op}.pbtxt"
            )

    def fetch(item: tuple[str, str]) -> dict:
        name, url = item
        try:
            with urlopen(url, timeout=45) as response:
                data = response.read()
            path = output / "specifications" / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
            return {
                "path": str(path.relative_to(output)),
                "url": url,
                "sha256": sha(data),
                "status": "downloaded",
            }
        except Exception as error:  # noqa: BLE001 -- retain acquisition/execution failures as evidence
            return {"url": url, "status": "unavailable", "error": type(error).__name__}

    with ThreadPoolExecutor(max_workers=4) as pool:
        documents = list(pool.map(fetch, specs.items()))
    save(output / "specifications.lock.json", documents)
    torch_doc = next(
        (d for d in documents if d.get("path") == "specifications/torch-docs.py"), None
    )
    if not torch_doc:
        raise ValueError("Required source specification unavailable")
    doc_tree = ast.parse((output / torch_doc["path"]).read_text())
    registry = []
    for family in FAMILIES:
        calls = [
            node
            for node in ast.walk(doc_tree)
            if isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and ast.unparse(node.args[0]) == f"torch.{family}"
        ]
        if len(calls) != 1:
            raise ValueError(f"Cannot uniquely locate source documentation: {family}")
        node = calls[0]
        tf_doc = next(
            (d for d in documents if d.get("path") == f"specifications/tf-{family}.pbtxt"), None
        )
        registry.append(
            {
                "id": family,
                "origin": "researcher-constructed-source-contract",
                "clauses": [
                    "elementwise-mathematical-value",
                    "input-shape-preserved",
                    "input-floating-dtype-preserved",
                ],
                "domain": {
                    "dtypes": ["float32", "float64"],
                    "rank_max": 4,
                    "elements_max": 4096,
                    "finite": True,
                    "closed_interval": bounds(family),
                },
                "reference": {
                    "implementation": "source_property_reference.py:scalar_reference",
                    "kind": "Python scalar math, computed from typed source inputs without target observations",
                    "float32": {"atol": 1e-7, "rtol": 1e-5},
                    "float64": {"atol": 1e-12, "rtol": 1e-12},
                    "scope": "bounded numerical evidence; not a proof or arbitrary-precision oracle",
                },
                "evidence": [{**torch_doc, "start_line": node.lineno, "end_line": node.end_lineno}]
                + ([tf_doc] if tf_doc else []),
                "exclusions": "Outside declared interval, nonfinite, complex/integer/sparse/quantized tensors, gradients, out= and device-specific semantics are not covered.",
            }
        )
    save(output / "source-properties.json", registry)

    candidates = []
    dllens = ROOT / "tmp/baseline-sources/dllens"
    for framework in ["pytorch", "tensorflow"]:
        directory = dllens / f"data/working_dir/rq1/dllens/{framework}/counterparts"
        for path in sorted(directory.glob("*.json")):
            name = path.stem
            # Include top-level / tf.math aliases, but no modules or Tensor methods.
            if not (
                name.startswith("torch.")
                and name.count(".") == 1
                or name.startswith("tf.")
                and (name.count(".") == 1 or name.startswith("tf.math."))
            ):
                continue
            family = ALIASES.get(name.split(".")[-1], name.split(".")[-1])
            if family not in FAMILIES:
                continue
            relative = str(path.relative_to(dllens))
            raw = upstream("dllens", relative)
            data = json.loads(raw)
            if len(data["inputs"]) != 1:
                raise ValueError(f"Unexpected source signature: {name}")
            target = "tensorflow" if framework == "pytorch" else "pytorch"
            record = {
                "id": f"D{len(candidates) + 1:04d}",
                "group": family,
                "source_framework": framework,
                "target_framework": target,
                "source_api": name,
                "argument": data["inputs"][0],
                "source_code": data["counterparts"][framework],
                "target_code": data["counterparts"][target],
                "upstream_path": relative,
                "upstream_sha256": sha(raw.encode()),
                "upstream_commit": "0f617e92c34d60bfdd3bc06d80c17d938879ed9c",
                "public_sample_inputs": data["sample_inputs"],
                "input_origin": "locally-constructed-source-domain-inputs",
                "partition": "discovery",
                "independence_unit": family,
            }
            candidates.append(record)
    save(output / "dllens-candidates.json", candidates)

    models = []
    besser = ROOT / "tmp/baseline-sources/besser-nn-migration"
    for directory in sorted((besser / "output").iterdir()):
        if not directory.is_dir():
            continue
        files = {}
        for framework, filename in [
            ("pytorch", "pytorch_nn_subclassing.py"),
            ("tensorflow", "tf_nn_subclassing.py"),
        ]:
            path = directory / filename
            content = path.read_text()
            node = next(
                n
                for n in ast.parse(content).body
                if isinstance(n, ast.ClassDef) and n.name == "NeuralNetwork"
            )
            files[framework] = {
                "path": str(path.relative_to(besser)),
                "sha256": sha(path.read_bytes()),
                "class_code": ast.get_source_segment(content, node),
                "start_line": node.lineno,
                "end_line": node.end_lineno,
            }
        models.append(
            {
                "id": directory.name,
                "source": "besser-nn-migration",
                "group": directory.name,
                "kind": "published-paired-network-definitions",
                "direction": "paired-definitions; migration-generation-history-not-established",
                "files": files,
                "property_origin": "output shape from source final layer; probability simplex only for source softmax",
                "original_shape_assertion": "EXP_random_inputs/test_functional_behavior.py:test_output_shape",
                "numerical_equivalence_status": "requires-aligned-weights-and-layout; not inferred from shape or random initialization",
            }
        )
    save(output / "besser-models.json", models)
    mappings = []
    tensorscope = ROOT / "tmp/baseline-sources/tensorscope"
    for path in sorted((tensorscope / "src/counterpart_api").glob("*.json")):
        data = json.loads(path.read_text())
        mappings.append(
            {
                "path": str(path.relative_to(tensorscope)),
                "entries": len(data),
                "sha256": sha(path.read_bytes()),
            }
        )
    save(
        output / "inventory.json",
        {
            "dllens": {
                "selected_candidates": len(candidates),
                "property_groups": len(registry),
                "total_existing_public_candidates": 1401,
            },
            "besser": {
                "paired_architectures": len(models),
                "model_files": 2 * len(models),
                "training_scripts": len(list((besser / "EXP_benchmark_datasets").glob("*.py"))),
                "completed_migration_outputs": 0,
            },
            "tensorscope": {
                "mapping_files": mappings,
                "tf2pt_converter_demo": "src/testing/tf2torch_op_test.py",
                "ready_pt_tf_pairs": 0,
                "status": "mapping/converter material; not counted as executed migration cases",
            },
            "specifications": {
                "downloaded": sum(d["status"] == "downloaded" for d in documents),
                "unavailable": sum(d["status"] != "downloaded" for d in documents),
            },
            "formal_accuracy_eligible": False,
        },
    )
    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "properties": len(registry),
                "paired_models": len(models),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    collect(parser.parse_args().output)
