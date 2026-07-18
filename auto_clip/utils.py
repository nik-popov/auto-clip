from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def stable_source_id(source: str) -> str:
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return digest[:12]


def run_command(command: list[str], dry_run: bool = False) -> None:
    if dry_run:
        print("[dry-run]", " ".join(command))
        return
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()[-600:]
        raise RuntimeError(
            f"Command failed ({result.returncode}): {command[0]} ... {stderr_tail}"
        )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
