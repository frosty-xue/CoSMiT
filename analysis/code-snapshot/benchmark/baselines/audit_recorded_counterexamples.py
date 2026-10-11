"""Audit the completed research-data campaign, without adding dataset entries.

Recompute archived checks; replay hash-matched existing controls in separate
framework interpreters. No model calls, no modifications to frozen records.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(fw, packet, output):
    import numpy as np
    lib = __import__("torch" if fw == "pytorch" else "tensorflow")
    if fw == "pytorch":
        lib.set_num_threads(1)
    else:
        lib.config.threading.set_inter_op_parallelism_threads(1)
        lib.config.threading.set_intra_op_parallelism_threads(1)
    rows = []
    for case in read(packet)["cases"]:
        for side in ("source", "target"):
            spec = case[side]
            if spec["framework"] != fw:
                continue
            for i, arguments in enumerate(case["inputs"]):
                for repeat in range(3):
                    env = {"np": np, "torch" if fw == "pytorch" else "tf": lib}
                    values = {name: (lib.tensor(np.asarray(arg["values"], dtype=arg["dtype"])) if fw == "pytorch"
                                    else lib.constant(np.asarray(arg["values"], dtype=arg["dtype"])))
                              for name, arg in arguments.items()}
                    calls = []
                    parts = spec["api"].split(".")
                    owner = lib
                    for part in parts[1:-1]:
                        owner = getattr(owner, part)
                    original = getattr(owner, parts[-1])

                    def wrapped(*a, **kw):
                        calls.append(spec["api"])
                        return original(*a, **kw)

                    try:
                        if side == "target":
                            setattr(owner, parts[-1], wrapped)
                        exec(compile(spec["code"], case["id"] + "-hash-matched-control", "exec"), env)
                        value = env[spec["entry"]](**values)
                        value = value.detach().numpy() if fw == "pytorch" and isinstance(value, lib.Tensor) else np.asarray(value)
                        observation = {"status": "ok", "value": value.tolist(), "dtype": str(value.dtype), "shape": list(value.shape), "calls": calls}
                    except Exception as error:
                        observation = {"status": "error", "error": type(error).__name__, "calls": calls}
                    finally:
                        setattr(owner, parts[-1], original)
                    rows.append({"case_id": case["id"], "side": side, "input_index": i, "repeat": repeat, "observation": observation})
    write(output, {"framework": fw, "version": lib.__version__, "numpy": np.__version__, "python": sys.version, "rows": rows})


def audit(args):
    import numpy as np
    from source_property_reference import scalar_reference, valid_input
    from unseen_properties import reference, valid_domain
    from verification_ports import digest
    sys.path.insert(0, str(ROOT / "src"))
    from cosmit.engine.certification import equal_values

    out, data = args.output.resolve(), args.data.resolve()
    out.mkdir(parents=True, exist_ok=False)
    issues, ledger, all_cases, all_rows, provenance = [], [], {}, {}, []
    for partition in ("controls", "discovery", "unseen"):
        cases = read(data / partition / "cases.json")
        grouped = defaultdict(list)
        with gzip.open(data / partition / "executions.jsonl.gz", "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                grouped[row["case_id"]].append(row)
        for c in cases:
            cid, contract = c["id"], c["contract"]
            all_cases[cid] = c
            rows = grouped[cid]
            all_rows[cid] = rows
            expected_ids = {(i, r) for i in range(len(c["inputs"])) for r in range(3)}
            assert len(rows) == len(expected_ids) and {(r["input_index"], r["repeat"]) for r in rows} == expected_ids
            if partition != "controls":
                codes = read(args.dllens / c["upstream_path"])["counterparts"]
                match = all(hashlib.sha256(codes[c[s]["framework"]].encode()).hexdigest() == c[s + "_code_sha256"] for s in ("source", "target"))
                provenance.append({"case_id": cid, "upstream_functions_match": match})
                if not match:
                    issues.append({"case_id": cid, "kind": "upstream-code-mismatch"})
            violation_inputs, source_checks, invalid_inputs = set(), 0, []
            for row in rows:
                i = row["input_index"]
                arguments = c["inputs"][i]
                arg = next(a for a in arguments.values() if a["kind"] == "tensor")
                array = np.asarray(arg["values"], dtype=arg["dtype"])
                tol = contract.get("tolerance_by_dtype", {}).get(arg["dtype"], {k: contract[k] for k in ("atol", "rtol")})
                if partition == "discovery":
                    valid = valid_input(array, contract["registered_domain"], np)
                    expected = np.asarray([scalar_reference(c["group"], float(x)) for x in array.flat]).reshape(array.shape)
                elif partition == "unseen":
                    names, family = c["argument_names"], c["group"]
                    other = np.asarray(arguments[names[1]]["values"], dtype=arg["dtype"]) if family == "matmul" else None
                    axis = arguments[names[1]]["value"] if family in {"prod", "cumsum", "cumprod"} else 0
                    keep = arguments[names[2]]["value"] if family == "prod" else False
                    valid = valid_domain(family, array, other, axis, np) and type(keep) is bool
                    if family == "matmul":
                        valid &= all(arguments[n]["value"] is (None if n == "output_type" else False) for n in names[2:])
                    if family in {"cumsum", "cumprod"}:
                        valid &= all(arguments[n]["value"] is False for n in names[2:])
                    expected = reference(family, array, other, axis, keep, np)
                else:
                    valid = array.ndim <= 4 and array.size <= 4096 and str(array.dtype) in {"float32", "float64"} and bool(np.isfinite(array).all())
                    expected = np.abs(array)
                if not valid:
                    invalid_inputs.append(i)
                src, dst = row["source"], row["target"]
                if src["status"] == "ok":
                    source_ok = src["shape"] == list(expected.shape) and src["dtype"] == str(array.dtype) and bool(np.allclose(src["value"], expected, **tol))
                    source_checks += 1
                    if not source_ok or row.get("source_reference_supported", source_ok) != source_ok:
                        issues.append({"case_id": cid, "input": i, "kind": "source-reference-disagrees"})
                if row["status"] != "executed":
                    continue
                assert {r["clause_id"] for r in row["clause_results"]} == set(contract["clauses"])
                for clause in row["clause_results"]:
                    kind = clause["clause_id"]
                    for side, observation in (("source", src), ("target", dst)):
                        # Unbound candidates may omit clause observations by design.
                        recorded = clause.get(side)
                        if recorded is not None and any(recorded.get(k) != observation[k] for k in ("value", "shape", "dtype")):
                            issues.append({"case_id": cid, "input": i, "kind": "clause-observation-mismatch", "side": side})
                    agrees = (equal_values(src["value"], dst["value"], **tol) if kind == "value" else src[kind] == dst[kind])
                    computed = "undetermined" if not dst["calls"] else "pass" if agrees else "violation"
                    if computed != clause["outcome"]:
                        issues.append({"case_id": cid, "input": i, "clause": kind, "kind": "clause-disagrees", "computed": computed, "recorded": clause["outcome"]})
                    if computed == "violation":
                        violation_inputs.add(i)
                # Dense numeric branch of the frozen DLLens comparator.
                a, b = (np.asarray(r["value"], dtype=r["dtype"]).squeeze().flatten() for r in (src, dst))
                agrees = a.size == b.size and bool(np.allclose(a, b, atol=0.1, rtol=1e-5, equal_nan=True))
                if agrees != row["dllens_agrees"]:
                    issues.append({"case_id": cid, "input": i, "kind": "dllens-comparator-disagrees"})
            stable = True
            for i in range(len(c["inputs"])):
                subset = [r for r in rows if r["input_index"] == i]
                signatures = [{s: {k: v for k, v in r[s].items() if k not in {"seconds", "message"}} for s in ("source", "target")} for r in subset]
                stable &= signatures[0] == signatures[1] == signatures[2]
            if invalid_inputs or not stable:
                issues.append({"case_id": cid, "kind": "invalid-input-or-unstable", "invalid_inputs": sorted(set(invalid_inputs)), "stable": stable})
            statuses = {r["status"] for r in rows}
            recomputed = dict.fromkeys(c["verdicts"], "undetermined")
            if "invalid-source-test" in statuses:
                recomputed = dict.fromkeys(recomputed, "invalid-source-test")
            elif statuses == {"executed"}:
                recomputed["self-test"] = "passed"
                recomputed["target-binding"] = "observed" if all(r["target"]["calls"] for r in rows) else "not-observed"
                recomputed["dllens-port"] = "no-difference-on-tested-inputs" if all(r["dllens_agrees"] for r in rows) else "difference-observed"
                if violation_inputs and stable:
                    recomputed["cosmit-registered-clauses"] = "refuted"
                elif all(all(cl["outcome"] == "pass" for cl in r["clause_results"]) for r in rows):
                    recomputed["cosmit-registered-clauses"] = "supported-on-tested-inputs"
            if recomputed != c["verdicts"]:
                issues.append({"case_id": cid, "kind": "case-verdict-mismatch", "computed": recomputed})
            ledger.append({"case_id": cid, "partition": partition, "family": c["group"], "source_api": c["source"]["api"], "target_api": c["target"]["api"],
                           "pairs": len(rows), "source_reference_rechecks": source_checks, "stable": stable,
                           "failing_input_indices": sorted(violation_inputs), "recorded_verdicts": c["verdicts"]})

    # On the registered small finite domain, the trunc bug has an exact predicate.
    trunc = all_cases["D0028"]
    predicted = []
    for i, arguments in enumerate(trunc["inputs"]):
        arg = next(iter(arguments.values()))
        x = np.asarray(arg["values"], dtype=arg["dtype"])
        if bool(((x < 0) & (x == np.floor(x))).any()):
            predicted.append(i)
    observed = next(r["failing_input_indices"] for r in ledger if r["case_id"] == "D0028")
    assert predicted == observed

    # Recover existing controls using the original constructor, then require exact code hashes.
    import build_development_packet as builder
    builder.upstream = lambda name, rel: (args.dllens / rel).read_text(encoding="utf-8")
    builder.build(out / "recovered-controls")
    packet = out / "recovered-controls/packet.json"
    for c in read(packet)["cases"]:
        old = all_cases[c["id"]]
        assert c["inputs"] == old["inputs"] and c["contract"] == old["contract"]
        assert digest([c["source"], c["target"]]) == old["reviewed_code_sha256"]
        for side in ("source", "target"):
            assert hashlib.sha256(c[side]["code"].encode()).hexdigest() == old[side + "_code_sha256"]
    replay_count = 0
    for fw, python in (("pytorch", args.pytorch_python), ("tensorflow", args.tensorflow_python)):
        command = [str(python), str(Path(__file__).resolve()), "--worker", fw, "--packet", str(packet), "--output", str(out / (fw + "-controls.json"))]
        process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                                 env=dict(os.environ, CUDA_VISIBLE_DEVICES="-1", TF_CPP_MIN_LOG_LEVEL="3", OMP_NUM_THREADS="1"))
        write(out / (fw + "-process.json"), {"command": command, "returncode": process.returncode, "stderr": process.stderr})
        assert process.returncode == 0, process.stderr
        for new in read(out / (fw + "-controls.json"))["rows"]:
            old = next(r[new["side"]] for r in all_rows[new["case_id"]] if r["input_index"] == new["input_index"] and r["repeat"] == new["repeat"])
            assert all(old[k] == v for k, v in new["observation"].items()), new
            replay_count += 1

    negative_models = []
    model_counts = {}
    for filename in ("model-primary.json", "model-retry.json"):
        records = read(data / filename)
        model_counts[filename] = dict(Counter(r["status"] for r in records))
        for r in records:
            if r["status"] == "completed" and (r["decision"].get("valid") is False or r["decision"].get("verdict") in {"violated", "invalid-test", "invalid-assumption", "undetermined"}):
                negative_models.append({k: r[k] for k in ("job_id", "case_id", "kind", "decision")} | {"view": filename, "executable_witness_provided": False})

    supplements = []
    for filename in ("tf-tutorial-observations.json", "lstm-observations.json", "alexnet-observations.json", "vgg16-observations.json"):
        d = read(data / "supplements" / filename)
        maxima = []
        for r in d["observations"]:
            a = np.asarray(r.get("source_values", r.get("source")))
            b = np.asarray(r.get("target_values", r.get("target")))
            delta = float(np.max(np.abs(a - b)))
            assert a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            assert delta == r["max_absolute_difference"]
            maxima.append(delta)
        supplements.append({"file": filename, "pairs": len(maxima), "max_absolute_difference_recomputed": max(maxima), "audit_level": "archived-observations-only"})
    tensor = read(data / "supplements/tensorscope.json")["records"]
    assert len({(r["input"], r["repeat"]) for r in tensor}) == len(tensor)
    for r in tensor:
        assert r["source"] == r["onnx"] == r["torch"] == [abs(r["value"])]
    supplements.append({"file": "tensorscope.json", "triplets": len(tensor), "all_recorded_values_match_integer_abs": True, "audit_level": "archived-observations-only"})
    write(out / "case-ledger.json", ledger)
    write(out / "provenance.json", provenance)
    write(out / "model-negative-decisions.json", negative_models)
    write(out / "supplements.json", supplements)
    write(out / "issues.json", issues)
    summary = {"scope": "research-data/2026-09-17 only; no pilot dataset or legacy RQ", "cases": len(ledger), "pairs_rechecked": sum(r["pairs"] for r in ledger),
               "source_reference_rechecks": sum(r["source_reference_rechecks"] for r in ledger), "public_code_hash_matches": sum(r["upstream_functions_match"] for r in provenance),
               "controls_replayed_single_executions": replay_count, "controls_match_historical_observations": True,
               "public_cases_with_violations": [r["case_id"] for r in ledger if r["partition"] != "controls" and r["failing_input_indices"]],
               "control_cases_with_violations": [r["case_id"] for r in ledger if r["partition"] == "controls" and r["failing_input_indices"]],
               "model_status_counts": model_counts, "audit_issues": len(issues), "model_calls": 0,
               "audit_script_sha256": sha(Path(__file__))}
    write(out / "summary.json", summary)
    write(out / "SHA256.json", {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=ROOT / "research-data/2026-09-17")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--dllens", type=Path)
    p.add_argument("--pytorch-python", type=Path)
    p.add_argument("--tensorflow-python", type=Path)
    p.add_argument("--worker", choices=["pytorch", "tensorflow"])
    p.add_argument("--packet", type=Path)
    args = p.parse_args()
    if args.worker:
        worker(args.worker, args.packet, args.output)
    else:
        audit(args)
