"""
SAVE: publish a month's outputs as one unit.

All files are written into a staging folder first; only when every file is written is the staging
folder swapped in for output/<month>/. A crash, or a run that halts, leaves the previous good
outputs untouched. Every file except the manifest is deterministic, so a rerun on the same
inputs is byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from .config import ROOT


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_version() -> dict:
    """Git commit of the code that produced the outputs, and whether the working tree had other edits."""
    try:
        # the last commit that touched code or config - committing outputs afterwards does not change it
        commit = subprocess.run(["git", "log", "-1", "--format=%h", "--", ".", ":!output", ":!data", ":!logs"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip() or None
        status = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!output", ":!data", ":!logs"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        return {"git_commit": commit, "uncommitted_changes": bool(status)}
    except Exception:
        return {"git_commit": None, "uncommitted_changes": None}


def publish(output_root: Path, month: str, frames: dict[str, pd.DataFrame], texts: dict[str, str], manifest: dict) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    staging = output_root / f".staging-{month}-{manifest['run_id']}"
    final, old = output_root / month, output_root / f".old-{month}-{manifest['run_id']}"
    staging.mkdir(parents=True)
    try:
        for name, df in frames.items():
            df.to_csv(staging / name, index=False, lineterminator="\n")
        for name, text in texts.items():
            (staging / name).write_text(text)
        manifest["outputs"] = {p.name: sha256(p)[:16] for p in sorted(staging.iterdir())}
        (staging / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
        if final.exists():
            os.replace(final, old)
        os.replace(staging, final)
        shutil.rmtree(old, ignore_errors=True)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if old.exists() and not final.exists():
            os.replace(old, final)
        raise
    return manifest["outputs"]


def write_run_log_manifest(log_root: Path, manifest: dict) -> Path:
    """Every run - including failed ones - leaves a manifest in logs/manifests/."""
    d = log_root / "manifests"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"run_{manifest['run_id']}_{manifest['month']}.json"
    p.write_text(json.dumps(manifest, indent=2, default=str))
    return p
