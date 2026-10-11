"""Inventory frozen public artifacts without executing generated programs."""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    dllens = ROOT / "tmp/baseline-sources/dllens"
    records, failures = [], []
    for library, direction in [("pytorch", "pt2tf"), ("tensorflow", "tf2pt")]:
        for path in sorted(
            (dllens / "data/working_dir/rq1/dllens" / library / "counterparts").glob("*.json")
        ):
            row = {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "direction": direction,
                "status": "unvalidated",
            }
            try:
                data = json.loads(path.read_text())
                row.update(
                    {
                        "function_name": data["function_name"],
                        "sample_input_count": len(data.get("sample_inputs", [])),
                        "llm_input_count": len(data.get("llm_inputs", [])),
                        "libraries": sorted(data["counterparts"]),
                    }
                )
                for code in data["counterparts"].values():
                    ast.parse(code)
                row["counterpart_syntax"] = "pass"
            except (ValueError, SyntaxError, TypeError, KeyError, AttributeError) as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                failures.append(row["path"])
            records.append(row)
    missing = []
    for path in sorted(dllens.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] not in {"codes", "utils"}:
                    continue
                base = dllens.joinpath(*node.module.split("."))
                if not base.with_suffix(".py").exists() and not base.is_dir():
                    missing.append(
                        {
                            "file": str(path.relative_to(dllens)),
                            "line": node.lineno,
                            "module": node.module,
                        }
                    )
    docter = ROOT / "tmp/baseline-sources/docter/constraints_extracted"
    constraints, yaml_errors = [], []
    for path in sorted(docter.rglob("*.yaml")):
        row = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "version_directory": path.relative_to(docter).parts[0],
        }
        try:
            data = yaml.safe_load(path.read_text())
            row.update(
                {
                    "api": data.get("title"),
                    "version": data.get("version"),
                    "constraint_parameters": len(data.get("constraints") or {}),
                }
            )
        except (yaml.YAMLError, TypeError, AttributeError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            yaml_errors.append(row["path"])
        constraints.append(row)
    rounds = {}
    for lib in ["tensorflow", "pytorch"]:
        # Same file/count expression as the first upstream RQ1 notebook cell.
        rounds[lib] = [
            len(
                (dllens / f"data/working_dir/rq1/dllens/{lib}/round{i}.txt")
                .read_text()
                .strip()
                .split("\n")
            )
            for i in range(1, 6)
        ]
    for name, rows in [
        ("dllens-candidates.jsonl", records),
        ("docter-constraints.jsonl", constraints),
    ]:
        (output / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    summary = {
        "schema_version": 1,
        "dllens_candidate_files": len(records),
        "dllens_directions": dict(collections.Counter(r["direction"] for r in records)),
        "dllens_total_sample_input_entries": sum(r.get("sample_input_count", 0) for r in records),
        "dllens_parse_or_schema_failures": failures,
        "dllens_missing_local_imports": missing,
        "upstream_rq1_first_cell_round_counts": rounds,
        "docter_constraint_files": len(constraints),
        "docter_version_directories": dict(
            collections.Counter(r["version_directory"] for r in constraints)
        ),
        "docter_yaml_failures": yaml_errors,
        "interpretation": "Availability/syntax inventory only; no semantic gold or independent sample count.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, list)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    audit(parser.parse_args().output)
