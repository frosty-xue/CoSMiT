"""Freeze reviewed upstream commits as private archives; verify without network access."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    "transfuzz": ("tmp/baseline-sources/transfuzz", "d6e79ca2f424fbdad379d5f139303cd81e7d6cbb"),
    "dllens": ("tmp/baseline-sources/dllens", "0f617e92c34d60bfdd3bc06d80c17d938879ed9c"),
    "docter": ("tmp/baseline-sources/docter", "fb49c2169779053edf8b6f80c81fc043aa06f804"),
    "intenttester": ("tmp/intenttest-baseline", "a906b7c49bbe0dec4d1d8b911e97281b7ce63063"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def freeze(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for name, (relative, commit) in PINS.items():
        repo = ROOT / relative
        if git(repo, "rev-parse", "HEAD").decode().strip() != commit:
            raise ValueError(f"{name}: unexpected commit")
        if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
            raise ValueError(f"{name}: tracked source modified")
        paths = git(repo, "ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0")
        files = [{"path": p, "sha256": sha256(repo / p)} for p in paths if p]
        archive = output / f"{name}-{commit}.tar.gz"
        archive.write_bytes(gzip.compress(git(repo, "archive", "--format=tar", commit), mtime=0))
        records.append(
            {
                "name": name,
                "checkout": relative,
                "commit": commit,
                "tree": git(repo, "rev-parse", "HEAD^{tree}").decode().strip(),
                "remote": git(repo, "remote", "get-url", "origin").decode().strip(),
                "commit_date": git(repo, "show", "-s", "--format=%cI", "HEAD").decode().strip(),
                "archive": archive.name,
                "archive_sha256": sha256(archive),
                "files": files,
            }
        )
    (output / "sources.lock.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "frozen_date": "2026-09-16",
                "sources": records,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({r["name"]: len(r["files"]) for r in records}))


def verify(output: Path) -> None:
    manifest = json.loads((output / "sources.lock.json").read_text())
    checks = 0
    for record in manifest["sources"]:
        archive = output / record["archive"]
        if sha256(archive) != record["archive_sha256"]:
            raise ValueError(f"archive hash mismatch: {archive}")
        checks += 1
        repo = ROOT / record["checkout"]
        if git(repo, "rev-parse", "HEAD").decode().strip() != record["commit"]:
            raise ValueError(f"commit changed: {repo}")
        for item in record["files"]:
            if sha256(repo / item["path"]) != item["sha256"]:
                raise ValueError(f"source hash mismatch: {repo / item['path']}")
            checks += 1
    print(json.dumps({"status": "pass", "hash_checks": checks}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "verify"])
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    (freeze if options.action == "freeze" else verify)(options.output)
