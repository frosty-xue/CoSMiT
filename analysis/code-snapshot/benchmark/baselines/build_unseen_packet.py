"""Assemble reserved public candidates only after source reference/input freeze."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from collect_public_corpus import ROOT, save, sha
from verification_ports import digest, upstream


def operation_calls(code: str, framework: str) -> list[str]:
    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted(node.value)
            return parent + "." + node.attr if parent else ""
        return ""

    prefix = "torch." if framework == "pytorch" else "tf."
    names = [dotted(n.func) for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Call)]
    return list(dict.fromkeys(n for n in names if n.startswith(prefix)))


def build(directory: Path) -> None:
    frozen = json.loads((directory / "pre-execution-freeze.json").read_text())
    for path, expected in frozen["files"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError("Pre-execution source protocol or method was modified")
    protocol = json.loads((directory / "protocol.freeze.json").read_text())
    inputs = json.loads((directory / "inputs.freeze.json").read_text())
    selection = json.loads((directory / "selection.exposure-audited.json").read_text())[
        "remaining_candidate_selection"
    ]
    cases = []
    for index, item in enumerate(selection):
        raw = upstream("dllens", item["relative_path"])
        if sha(raw.encode()) != item["sha256"]:
            raise ValueError("Unseen candidate source hash mismatch")
        data = json.loads(raw)
        family, framework = item["family"], item["framework"]
        other = "tensorflow" if framework == "pytorch" else "pytorch"
        argument_names = data["inputs"]
        arguments = []
        for sample in inputs[family]:
            args = {
                argument_names[0]: {
                    "kind": "tensor",
                    "dtype": sample["dtype"],
                    "values": sample["matrix"],
                }
            }
            if family == "matmul":
                args[argument_names[1]] = {
                    "kind": "tensor",
                    "dtype": sample["dtype"],
                    "values": sample["other"],
                }
                for name in argument_names[2:]:
                    args[name] = {
                        "kind": "literal",
                        "value": None if name == "output_type" else False,
                    }
            elif family in {"prod", "cumsum", "cumprod"}:
                args[argument_names[1]] = {"kind": "literal", "value": sample["axis"]}
                for name in argument_names[2:]:
                    args[name] = {
                        "kind": "literal",
                        "value": sample["keepdim"] if family == "prod" else False,
                    }
            arguments.append(args)
        source = {
            "framework": framework,
            "code": data["counterparts"][framework],
            "entry": framework + "_call",
            "api": item["api"],
        }
        calls = operation_calls(data["counterparts"][other], other)
        target = {
            "framework": other,
            "code": data["counterparts"][other],
            "entry": other + "_call",
            "api": calls[0] if calls else "unregistered",
            "apis": calls,
        }
        schema_root = ROOT / "tmp/baseline-sources/docter"
        schema = (
            schema_root
            / "constraints_extracted"
            / ("pytorch1.5" if framework == "pytorch" else "tensorflow2.1")
            / (item["api"] + ".yaml")
        )
        cases.append(
            {
                "id": f"H{index + 1:03d}",
                "group": family,
                "origin": "public-source-family-reserved-before-execution",
                "source": source,
                "target": target,
                "upstream_path": item["relative_path"],
                "reviewed_code_sha256": digest([source, target]),
                "argument_names": argument_names,
                "inputs": arguments,
                "docter_file": str(schema.relative_to(schema_root)) if schema.exists() else None,
                "contract": {
                    "domain_id": "reserved-matrix-ops-v1",
                    "family": family,
                    "description": protocol["source_references"][family]
                    + "; preserve operation-derived shape and input floating dtype on the registered domain.",
                    "clauses": ["value", "shape", "dtype"],
                    "domain": protocol["input_design"],
                    "exclusions": protocol["exclusions"],
                    "atol": 1e-6,
                    "rtol": 1e-5,
                    "tolerance_by_dtype": protocol["tolerance_by_dtype"],
                    "evidence": "fixed-version source specifications and independent scalar reference frozen before target inspection",
                },
            }
        )
    packet = {
        "schema_version": 3,
        "partition": "reserved-unseen-operation-families",
        "formal_eligible": False,
        "eligibility_reason": "Unseen-family finite evaluation; formal accuracy requires completed independent reference adjudication and all method results",
        "cases": cases,
        "budget": {
            "inputs_per_case": protocol["budget"]["inputs_per_case"],
            "executions_per_input": protocol["budget"]["repetitions"],
            "max_pairs_per_case": protocol["budget"]["max_pairs_per_case"],
        },
        "protocol_sha256": sha((directory / "protocol.freeze.json").read_bytes()),
        "input_sha256": sha((directory / "inputs.freeze.json").read_bytes()),
    }
    if (directory / "packet.json").exists():
        raise FileExistsError("Do not overwrite a frozen packet")
    save(directory / "packet.json", packet)
    print(
        json.dumps(
            {"candidates": len(cases), "groups": len(inputs), "model_requests": 5 * len(cases)}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    build(parser.parse_args().directory)
