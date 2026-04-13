#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Regenerate .claude-plugin/{plugin,marketplace}.json from SKILL.md frontmatter.

Source of truth:
  - .claude-plugin/plugin.json        → name, version, author (canonical)
  - plugins/forge/skills/*/SKILL.md   → frontmatter `name` + `summary` per skill

Generated:
  - plugin.json.description
  - marketplace.json.plugins[0].description
  - marketplace.json.plugins[0].version   ← mirrors plugin.json.version

Usage:
  scripts/gen-plugin-manifest.py           # regenerate in place
  scripts/gen-plugin-manifest.py --check   # exit 1 if out of sync (for pre-commit / CI)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO / ".claude-plugin" / "marketplace.json"
SKILLS_DIR = REPO / "plugins" / "forge" / "skills"

TAGLINE = "Forge HTML visuals for ~/.roxabi/forge/"
TAIL = "Brand-aware, manifest-indexed, Cloudflare Pages ready."


def parse_frontmatter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SystemExit(f"{md_path}: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SystemExit(f"{md_path}: unterminated frontmatter")
    return yaml.safe_load(text[4:end]) or {}


def collect_skills() -> list[tuple[str, str]]:
    skills: list[tuple[str, str]] = []
    for sk in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        fm = parse_frontmatter(sk)
        name = fm.get("name")
        summary = fm.get("summary")
        if not name or not summary:
            raise SystemExit(
                f"{sk.relative_to(REPO)}: frontmatter missing `name` and/or `summary`"
            )
        skills.append((name, summary))
    if not skills:
        raise SystemExit(f"no SKILL.md files found under {SKILLS_DIR}")
    return skills


def build_description(skills: list[tuple[str, str]]) -> str:
    parts = ", ".join(f"{n} ({s})" for n, s in skills)
    return f"{TAGLINE} — {parts}. {TAIL}"


def dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    skills = collect_skills()
    desc = build_description(skills)

    plugin = json.loads(PLUGIN_JSON.read_text())
    market = json.loads(MARKETPLACE_JSON.read_text())

    plugin_new = {**plugin, "description": desc}
    market_new = json.loads(json.dumps(market))  # deep copy
    market_new["plugins"][0]["description"] = desc
    market_new["plugins"][0]["version"] = plugin["version"]

    changes: list[str] = []
    if plugin_new != plugin:
        changes.append("plugin.json")
    if market_new != market:
        changes.append("marketplace.json")

    if args.check:
        if changes:
            print(
                f"✗ manifests out of sync: {', '.join(changes)} — "
                f"run scripts/gen-plugin-manifest.py",
                file=sys.stderr,
            )
            return 1
        print("✓ manifests in sync", file=sys.stderr)
        return 0

    if changes:
        PLUGIN_JSON.write_text(dump(plugin_new), encoding="utf-8")
        MARKETPLACE_JSON.write_text(dump(market_new), encoding="utf-8")
        print(f"✓ regenerated: {', '.join(changes)}", file=sys.stderr)
    else:
        print("✓ no changes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
