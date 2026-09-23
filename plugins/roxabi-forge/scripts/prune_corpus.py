#!/usr/bin/env python3
"""Archive a forge tree, then drop the test corpus. Never touches the live tree unless asked."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

CORE = frozenset(
    {
        "_shared/hero-base.css",
        "_shared/hero-base.js",
        "_shared/gallery-base.css",
        "_shared/gallery-base.js",
        "_shared/fgraph-base.css",
        "_shared/explainer-base.css",
    }
)
LIVE_ROOT = Path.home() / ".roxabi" / "forge"
ARCHIVE_SKIP_NAMES = frozenset({".env", "_dist", ".wrangler"})
EXAMPLE_DIRS = frozenset({"examples"})


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _skip_archive(rel: str) -> bool:
    name = Path(rel).name
    if name in ARCHIVE_SKIP_NAMES or name == ".wrangler" or rel.startswith(".wrangler/") or rel.startswith("_dist/"):
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    return False


def dropped(rel: str) -> bool:
    """True when this relative path is part of the cut."""
    if rel in CORE:
        return False
    if rel == "_test-forge" or rel.startswith("_test-forge/"):
        return True
    if rel == "reference-gallery.html":
        return True
    parts = rel.split("/")
    if parts[0] == "references" and EXAMPLE_DIRS.intersection(parts):
        return True
    if rel == "references/showcases" or rel.startswith("references/showcases/"):
        return True
    if rel.startswith("_shared/") and rel.endswith(".html"):
        return True
    if rel.startswith("_shared/diagrams/") or rel.startswith("_shared/guides/"):
        return True
    return False


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _skip_archive(_rel(root, Path(dirpath) / d))]
        for name in filenames:
            path = Path(dirpath) / name
            rel = _rel(root, path)
            if _skip_archive(rel):
                continue
            out.append(path)
    return out


def archive_tree(root: Path, archive: Path) -> int:
    if archive.exists():
        raise FileExistsError(f"archive already exists: {archive}")
    archive.mkdir(parents=True)
    copied = 0
    for path in iter_files(root):
        rel = _rel(root, path)
        dest = archive / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            dest.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, dest)
        copied += 1
    return copied


def prune_tree(root: Path) -> list[str]:
    removed: list[str] = []
    for path in sorted(iter_files(root), key=lambda p: len(_rel(root, p)), reverse=True):
        rel = _rel(root, path)
        if not dropped(rel):
            continue
        path.unlink()
        removed.append(rel)
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        current = Path(dirpath)
        if current == root:
            continue
        rel = _rel(root, current)
        if dropped(rel) and not any(current.iterdir()):
            current.rmdir()
    return removed


def run(root: Path, archive: Path, live: bool) -> int:
    root = root.resolve()
    if root == LIVE_ROOT.resolve() and not live:
        print(f"refusing live tree {root} without --live", file=sys.stderr)
        return 2
    copied = archive_tree(root, archive)
    archived = list(iter_files(archive))
    if len(archived) != copied:
        print("archive check failed; not pruning", file=sys.stderr)
        return 1
    prune_tree(root)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    return run(args.root, args.archive, args.live)


if __name__ == "__main__":
    raise SystemExit(main())
