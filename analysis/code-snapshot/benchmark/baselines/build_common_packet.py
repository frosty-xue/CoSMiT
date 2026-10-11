"""Join frozen public code, source-only properties and the identical 64-input budget."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from collect_public_corpus import ROOT, save, sha
from verification_ports import digest, upstream


def target_api(code: str) -> str:
    function = ast.parse(code).body[0]
    expression = function.body[-1].value
    if isinstance(expression, ast.Call):
        return ast.unparse(expression.func)
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        return "torch.Tensor.__rtruediv__"
    if isinstance(expression, ast.BinOp) and isinstance(expression.left, ast.Call):
        return ast.unparse(expression.left.func)
    raise ValueError("Target expression needs explicit operation registration")


def build(corpus: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    properties = {p["id"]: p for p in json.loads((corpus / "source-properties.json").read_text())}
    inputs = json.loads((corpus / "unary-execution/inputs.json").read_text())
    public = json.loads((corpus / "dllens-candidates.json").read_text())
    docter = ROOT / "tmp/baseline-sources/docter/constraints_extracted"
    cases = []
    for candidate in public:
        raw = upstream("dllens", candidate["upstream_path"])
        if sha(raw.encode()) != candidate["upstream_sha256"]:
            raise ValueError("Public candidate provenance mismatch")
        original = json.loads(raw)
        for side in ["source", "target"]:
            if (
                candidate[side + "_code"]
                != original["counterparts"][candidate[side + "_framework"]]
            ):
                raise ValueError("Public code was modified")
        family = candidate["group"]
        prop = properties[family]
        source = {
            "framework": candidate["source_framework"],
            "code": candidate["source_code"],
            "entry": candidate["source_framework"] + "_call",
            "api": candidate["source_api"],
        }
        target = {
            "framework": candidate["target_framework"],
            "code": candidate["target_code"],
            "entry": candidate["target_framework"] + "_call",
            "api": target_api(candidate["target_code"]),
        }
        schema_dir = docter / (
            "pytorch1.5" if source["framework"] == "pytorch" else "tensorflow2.1"
        )
        schema = schema_dir / (source["api"] + ".yaml")
        if not schema.exists() and source["framework"] == "tensorflow":
            alias = "tf.math." + source["api"].split(".")[-1]
            schema = schema_dir / (alias + ".yaml")
        cases.append(
            {
                "id": candidate["id"],
                "group": family,
                "source": source,
                "target": target,
                "origin": "dllens-public-functions-with-constructed-source-properties",
                "upstream_path": candidate["upstream_path"],
                "reviewed_code_sha256": digest([source, target]),
                "contract": {
                    "domain_id": "bounded-unary-v1",
                    "family": family,
                    "description": f"For inputs in the registered domain, preserve the elementwise mathematical {family} value, input shape and floating dtype.",
                    "clauses": ["value", "shape", "dtype"],
                    "registered_domain": prop["domain"],
                    "atol": 1e-7,
                    "rtol": 1e-5,
                    "tolerance_by_dtype": {
                        dtype: prop["reference"][dtype] for dtype in ["float32", "float64"]
                    },
                    "evidence": prop["evidence"],
                },
                "inputs": [
                    {
                        candidate["argument"]: {
                            "kind": "tensor",
                            "dtype": item["dtype"],
                            "values": item["values"],
                        }
                    }
                    for item in inputs[family]
                ],
                "docter_file": str(schema.relative_to(docter.parent)) if schema.exists() else None,
            }
        )
    packet = {
        "schema_version": 3,
        "partition": "public-discovery-exposed-families",
        "formal_eligible": False,
        "cases": cases,
        "budget": {"inputs_per_case": 64, "executions_per_input": 3, "max_pairs_per_case": 192},
        "source_corpus_hash": sha((corpus / "dllens-candidates.json").read_bytes()),
        "input_file_hash": sha((corpus / "unary-execution/inputs.json").read_bytes()),
        "source_property_hash": sha((corpus / "source-properties.json").read_bytes()),
    }
    save(output / "packet.json", packet)
    save(
        output / "exposure-exclusions.json",
        {
            "excluded_from_unseen_family_holdout": sorted(properties),
            "rule": "both directions, Tensor methods, tf.math/nn/Keras wrappers and mathematical synonyms of these families are exposed",
            "status": "exclusion list only; unseen groups not yet frozen or evaluated",
        },
    )
    print(
        json.dumps(
            {
                "cases": len(cases),
                "groups": len(properties),
                "schemas": sum(c["docter_file"] is not None for c in cases),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.corpus, args.output)
