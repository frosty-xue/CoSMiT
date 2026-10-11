"""Create pipeline controls with a SEPARATE key; no controls enter formal evaluation."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from verification_ports import digest, mutate_inputs, upstream


def build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    cases, key = [], []
    for framework, filename in [("pytorch", "torch.Tensor.abs"), ("tensorflow", "tf.abs")]:
        relative = f"data/working_dir/rq1/dllens/{framework}/counterparts/{filename}.json"
        data = json.loads(upstream("dllens", relative))
        other = "tensorflow" if framework == "pytorch" else "pytorch"
        arg = data["inputs"][0]
        source = {
            "framework": framework,
            "code": data["counterparts"][framework],
            "entry": framework + "_call",
            "api": filename,
        }
        target = {
            "framework": other,
            "code": data["counterparts"][other],
            "entry": other + "_call",
            "api": "tf.abs" if other == "tensorflow" else "torch.abs",
        }
        base = {
            "source": source,
            "target": target,
            "group": "absolute-value",
            "origin": "dllens-public-functions-with-locally-constructed-contract-and-inputs",
            "upstream_path": relative,
            "contract": {
                "domain_id": "finite-dense-floats-v1",
                "description": "For finite real floating tensors, return elementwise absolute values with the same shape and dtype.",
                "clauses": ["value", "shape", "dtype"],
                "atol": 1e-6,
                "rtol": 1e-5,
                "domain": "finite float32/float64 dense tensor; rank <= 4; <= 4096 elements",
                "evidence": "public abs functions and source API documentation referenced by DocTer",
            },
            "docter_file": "constraints_extracted/pytorch1.5/torch.abs.yaml"
            if framework == "pytorch"
            else "constraints_extracted/tensorflow2.1/tf.math.abs.yaml",
            "inputs": [
                {arg: {"kind": "tensor", "dtype": "float32", "values": [[-2.0, 1.0], [0.0, -3.0]]}},
                {
                    arg: {
                        "kind": "tensor",
                        "dtype": "float32",
                        "values": [[0.0, -1e-6], [1e-6, -1.0]],
                    }
                },
            ],
        }
        base["inputs"][1] = mutate_inputs(base["inputs"][0], 20260916)
        for variant in ["original", "flatten", "bias", "bypass", "invalid-source"]:
            case = copy.deepcopy(base)
            case["id"] = f"C{len(cases) + 1:03d}"
            if variant != "original":
                case["origin"] = "constructed-development-control"
            code = target["code"]
            if variant in {"flatten", "bias"}:
                expression = code.split("return ", 1)[1].strip()
                expression = (
                    (
                        f"tf.reshape({expression}, [-1])"
                        if other == "tensorflow"
                        else f"({expression}).reshape(-1)"
                    )
                    if variant == "flatten"
                    else f"({expression}) + 0.05"
                )
                case["target"]["code"] = code.split("return ", 1)[0] + "return " + expression
            elif variant == "bypass":
                case["target"]["code"] = (
                    f"def {other}_call({arg}):\n    return np.abs(np.asarray({arg}))"
                )
            elif variant == "invalid-source":
                case["source"]["code"] = (
                    f"def {framework}_call({arg}):\n    assert False, 'invalid source assertion'\n    return {arg}"
                )
            case["reviewed_code_sha256"] = digest([case["source"], case["target"]])
            cases.append(case)
            key.append(
                {
                    "case_id": case["id"],
                    "construction": variant,
                    "expected_cosmit": "refuted"
                    if variant in {"flatten", "bias"}
                    else "undetermined"
                    if variant == "bypass"
                    else "invalid-source-test"
                    if variant == "invalid-source"
                    else "supported-on-tested-inputs",
                }
            )
    packet = {
        "schema_version": 2,
        "partition": "development-controls",
        "cases": cases,
        "budget": {"inputs_per_case": 2, "executions_per_input": 3, "max_pairs_per_case": 6},
        "allowed_holdout_groups": [],
        "formal_eligible": False,
    }
    (output / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    (output / "control-key.json").write_text(json.dumps(key, indent=2) + "\n")
    (output / "packet.sha256").write_text(digest(packet) + "\n")
    print(f"Prepared {len(cases)} development cases; separate control key; no framework execution")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
