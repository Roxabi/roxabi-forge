"""Shared path resolution for forge scripts — repo checkout vs ~/.roxabi/forge layout."""

from __future__ import annotations

import os
from pathlib import Path

_MARKER = Path("graph-templates") / "fd-shell.html"


def script_root(script_file: str | Path) -> Path:
    """Parent of scripts/ — repo root or ~/.roxabi/forge."""
    return Path(script_file).resolve().parent.parent


def forge_ref_candidates(root: Path) -> list[Path]:
    env = os.environ.get("FORGE_REF")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser().resolve())
    candidates.extend(
        [
            root / "plugins" / "forge" / "references",
            root / "references",
        ]
    )
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def resolve_forge_ref(root: Path) -> Path:
    for candidate in forge_ref_candidates(root):
        if (candidate / _MARKER).exists():
            return candidate
    tried = ", ".join(str(p) for p in forge_ref_candidates(root))
    raise FileNotFoundError(
        f"forge references not found (need {_MARKER}); tried: {tried}"
    )


def default_expect_path(root: Path) -> Path | None:
    candidates = [
        root
        / "plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.expect.json",
        root / "scripts/fixtures/lyra-stack-v2.expect.json",
        root / "fixtures/lyra-stack-v2.expect.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def default_fixture_path(root: Path) -> Path | None:
    candidates = [
        root / "plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.json",
        root / "scripts/fixtures/lyra-stack-v2.json",
        root / "fixtures/lyra-stack-v2.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None