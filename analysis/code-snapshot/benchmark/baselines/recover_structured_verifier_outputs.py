"""Offline parsing sensitivity; retain strict primary outcomes and make zero requests."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from collect_public_corpus import save, sha
from verification_ports import digest, parse_model_answer


def recover(response: dict, kind: str) -> dict:
    choice = response["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Truncated response cannot be recovered")
    text = choice["message"]["content"]
    if text.lower().count("<think>") != text.lower().count("</think>"):
        raise ValueError("Unclosed reasoning block")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    blocks = list(re.finditer(r"```(?:json)?\s*\n?(.*?)```", text, flags=re.DOTALL))
    if len(blocks) != 1 or text[blocks[0].end() :].strip():
        raise ValueError("Require exactly one final fenced answer")
    return parse_model_answer(blocks[0].group(1), kind)


def run(primary: Path, output: Path) -> None:
    if not (primary / "summary.json").exists():
        raise ValueError("Primary batch is still running")
    output.mkdir(parents=True, exist_ok=False)
    selected = json.loads((primary / "selected-jobs.json").read_text())
    save(output / "selected-jobs.json", selected)
    counts = {"primary_completed": 0, "recovered": 0, "unresolved": 0}
    for job in selected:
        path = primary / (job["job_id"] + ".json")
        record = json.loads(path.read_text())
        if (
            record["prompt_sha256"] != job["prompt_sha256"]
            or digest(job["prompt"]) != job["prompt_sha256"]
        ):
            raise ValueError("Prompt/response mismatch")
        record["primary_status"] = record["status"]
        record["primary_file_sha256"] = sha(path.read_bytes())
        record["primary_file"] = str(path.resolve())
        if record["status"] == "completed":
            counts["primary_completed"] += 1
        else:
            try:
                record["parsed"] = recover(record["response"], record["kind"])
                record["status"] = "completed"
                record["recovery_rule"] = (
                    "single-final-fenced-typed-JSON; supplementary parsing sensitivity only"
                )
                counts["recovered"] += 1
            except (KeyError, IndexError, TypeError, ValueError):
                counts["unresolved"] += 1
        save(output / path.name, record)
    save(
        output / "summary.json",
        {
            **counts,
            "original_attempts": len(selected),
            "additional_model_calls": 0,
            "analysis_role": "supplementary post-hoc parsing sensitivity; never replaces strict primary results",
            "script_sha256": sha(Path(__file__).read_bytes()),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("primary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.primary, args.output)
