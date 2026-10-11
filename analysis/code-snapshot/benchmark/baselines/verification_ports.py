"""Locally authored fixed-candidate ports; no upstream fuzzer stubs or gold labels."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import random
import re
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "artifacts/baselines/20260916-v1/sources/sources.lock.json"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def upstream(name: str, relative: str) -> str:
    record = next(r for r in json.loads(LOCK.read_text())["sources"] if r["name"] == name)
    expected = next(r["sha256"] for r in record["files"] if r["path"] == relative)
    content = (ROOT / record["checkout"] / relative).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("upstream file differs from frozen commit")
    return content.decode()


def dllens_comparator(np: Any) -> Any:
    code = upstream("dllens", "codes/counterpart/evaluate_counterpart.py")
    names = {"compare_res", "convert_to_numpy", "sparse_to_dense"}
    nodes = [n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(nodes) != 3:
        raise ValueError("upstream comparator missing")
    namespace = {"np": np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "dllens-frozen", "exec"), namespace)  # noqa: S102 -- verified upstream functions
    return namespace["compare_res"]


def tensor_shape(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    subshapes = [tensor_shape(v) for v in values]
    if subshapes and any(s != subshapes[0] for s in subshapes):
        raise ValueError("ragged input")
    return [len(values)] + (subshapes[0] if subshapes else [])


def leaves(values: Any) -> list[Any]:
    return [v for part in values for v in leaves(part)] if isinstance(values, list) else [values]


def mutate_inputs(arguments: dict[str, Any], seed: int) -> dict[str, Any]:
    """Bounded finite-value mutation; keeps argument names, shapes and dtypes."""
    result = copy.deepcopy(arguments)
    rng = random.Random(seed)
    choices = [-1.0, -1e-6, 0.0, 1e-6, 1.0]

    def mutate(values: Any) -> Any:
        return [mutate(v) for v in values] if isinstance(values, list) else rng.choice(choices)

    for arg in result.values():
        if arg["kind"] != "tensor" or arg["dtype"] not in {"float32", "float64"}:
            raise ValueError("unsupported mutation domain")
        arg["values"] = mutate(arg["values"])
    return result


def check_docter(schema: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """Evaluate documented literal fields; symbolic/unknown fields MUST abstain.

    This reports satisfaction of the published historical schema, not correctness
    of the oracle or automatic compatibility with a newer framework version.
    """
    checks = []
    for name in schema.get("inputs", {}).get("required", []):
        checks.append({"parameter": name, "field": "required", "result": name in arguments})
    metadata = {"descp", "doc_dtype", "default"}
    for name, rules in (schema.get("constraints") or {}).items():
        if name not in arguments:
            continue
        arg = arguments[name]
        value = arg.get("values", arg.get("value"))
        shape = tensor_shape(value)
        for field, allowed in rules.items():
            if field in metadata:
                continue
            result = None
            if isinstance(allowed, list) and allowed:
                if field == "tensor_t":
                    known = {
                        "torch.tensor",
                        "tf.tensor",
                        "tf.Tensor",
                        "tensorflow.Tensor",
                        "SparseTensor",
                    }
                    if all(a in known for a in allowed):
                        result = arg["kind"] == "tensor" and any(
                            a != "SparseTensor" for a in allowed
                        )
                elif field == "structure" and all(a in {"list", "tuple"} for a in allowed):
                    result = arg["kind"] in allowed
                elif field == "ndim" and all(str(a).isdigit() for a in allowed):
                    result = len(shape) in [int(a) for a in allowed]
                elif field == "dtype" and all(isinstance(a, str) for a in allowed):
                    known = {
                        "int",
                        "float",
                        "bool",
                        "str",
                        "int32",
                        "int64",
                        "float16",
                        "float32",
                        "float64",
                        "complex64",
                        "complex128",
                    }
                    allowed = [a.removeprefix("tf.").removeprefix("torch.") for a in allowed]
                    if all(a in known for a in allowed):
                        actual = arg.get("dtype", type(value).__name__)
                        result = actual in allowed
                        if arg["kind"] == "tensor":
                            result = result or ("int" in allowed and actual.startswith("int"))
                            result = result or ("float" in allowed and actual.startswith("float"))
                        else:
                            if "int" in allowed:
                                result = result or all(type(v) is int for v in leaves(value))
                            if "float" in allowed:
                                result = result or all(type(v) is float for v in leaves(value))
                elif field == "enum" and all(type(a) in {int, float, bool} for a in allowed):
                    result = value in allowed
            checks.append({"parameter": name, "field": field, "result": result})
    state = (
        "violated"
        if any(c["result"] is False for c in checks)
        else "undetermined"
        if not checks or any(c["result"] is None for c in checks)
        else "satisfied"
    )
    return {
        "state": state,
        "checks": checks,
        "schema_version": schema.get("version"),
        "schema_api": schema.get("title"),
        "current_version_compatibility": "not-established",
    }


def java_prompt(filename: str, variable: str) -> str:
    code = upstream("intenttester", "src/main/java/framework/" + filename)
    match = re.search(r"\b" + re.escape(variable) + r'\s*=\s*"""(.*?)""";', code, re.DOTALL)
    if not match:
        raise ValueError("missing original Java text block")
    return textwrap.dedent(match.group(1)).strip()


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def prepare_llm_jobs(case: dict[str, Any], trace: dict[str, Any]) -> list[dict[str, Any]]:
    # Explicit allowlist prevents reference labels, CoSMiT decisions and paths leaking.
    context = {k: case[k] for k in ["source", "target", "inputs", "contract"]}
    setup = "import numpy as np\nimport tensorflow as tf\nimport torch\n"
    context["execution_setup"] = setup
    context["framework_versions"] = trace.get("versions", {})
    generic = (
        "Review this fixed cross-framework test migration. Use the supplied contract, "
        "but check whether its assumptions are justified by the source test. "
        "Separate invalid source tests/assumptions from property non-preservation. "
        "Return JSON {verdict: preserved|violated|invalid-test|invalid-assumption|undetermined, "
        "reason: string}. Do not assume passing executions prove universal preservation.\n"
    )
    # TDL is derived from a source-only declared contract, not from reference labels.
    tdl = {
        "metadata": {"goal": case["contract"]["description"]},
        "inputs": {"content": case["inputs"]},
        "assertions": case["contract"]["clauses"],
    }
    intent = java_prompt("VerificationAgent.java", "INTENT_USER_PROMPT")
    usage = java_prompt("VerificationAgent.java", "TEST_USER_PROMPT")
    suffix = '\nAdapter output contract: return JSON {"valid": true|false|null, "reason": "..."}.'
    raw_trace = {"records": trace.get("records", []), "execution_status": trace.get("status")}
    # Remove results of every verifier; only source/target observations remain.
    raw_trace["records"] = [
        {k: r[k] for k in ["input_index", "repeat", "source", "target"] if k in r}
        for r in raw_trace["records"]
    ]
    prompts = [
        ("direct-llm", generic + json.dumps(context)),
        ("trace-llm", generic + json.dumps({**context, "observations": raw_trace})),
        (
            "intenttester-source-tdl",
            render(
                intent, {"testIntent": json.dumps(tdl), "testCode": setup + case["source"]["code"]}
            )
            + suffix,
        ),
        (
            "intenttester-target-api",
            render(usage, {"intentTest": setup + case["target"]["code"]}) + suffix,
        ),
        (
            "intenttester-target-tdl-extension",
            render(
                intent, {"testIntent": json.dumps(tdl), "testCode": setup + case["target"]["code"]}
            )
            + suffix,
        ),
    ]
    return [
        {
            "case_id": case["id"],
            "kind": kind,
            "prompt": prompt,
            "job_id": digest([case["id"], kind])[:20],
            "prompt_sha256": digest(prompt),
        }
        for kind, prompt in prompts
    ]


def parse_model_answer(text: str, kind: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if not match:
            raise ValueError("malformed fenced JSON")
        text = match.group(1)
    result = json.loads(text)
    if not isinstance(result, dict) or not isinstance(result.get("reason"), str):
        raise TypeError("invalid answer schema")
    if kind.startswith("intenttester-"):
        if "valid" not in result or (
            result["valid"] is not None and type(result["valid"]) is not bool
        ):
            raise ValueError("valid must be boolean or null")
    elif result.get("verdict") not in {
        "preserved",
        "violated",
        "invalid-test",
        "invalid-assumption",
        "undetermined",
    }:
        raise ValueError("invalid verdict")
    return result


def aggregate_checks(checks: list[bool | None]) -> str:
    if any(c is False for c in checks):
        return "rejected"
    return "accepted" if checks and all(c is True for c in checks) else "undetermined"
