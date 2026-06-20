#!/usr/bin/env python3
"""
validate-fd.py — layout + integrity gate for gen-fd.py HTML output.

Static checks (no browser): placeholders, fd-data, bundle symbols.
Browser checks (Playwright): node positioning, canvas bounds, spacing pairs.

Usage:
  python3 scripts/validate-fd.py --html diagram.html
  python3 scripts/validate-fd.py --html diagram.html --expect fixtures/lyra-stack-v2.expect.json
  python3 scripts/validate-fd.py --in descriptor.json --out /tmp/out.html --expect ...  # gen + validate

Requires Playwright for browser checks (skipped with --static-only):
  uv run --with playwright python3 scripts/validate-fd-browser.py ...
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))
from forge_paths import default_expect_path, script_root  # noqa: E402

ROOT = script_root(__file__)
BROWSER_SCRIPT = _SCRIPTS_DIR / "validate-fd-browser.py"
DEFAULT_EXPECT = default_expect_path(ROOT)
PLACEHOLDER_RE = re.compile(r"\{[A-Z][A-Z0-9_]+\}")
FD_DATA_RE = re.compile(
    r'<script[^>]+id="fd-data"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class Finding:
    level: str  # error | warn
    code: str
    message: str
    detail: Any = None

    def format(self) -> str:
        line = f"[{self.level.upper()}] {self.code}: {self.message}"
        if self.detail is not None:
            line += f" — {self.detail}"
        return line


def load_expect(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def static_checks(html_path: Path, expect: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    text = html_path.read_text(encoding="utf-8")

    placeholders = PLACEHOLDER_RE.findall(text)
    if placeholders:
        findings.append(
            Finding(
                "error",
                "placeholder",
                f"unfilled template token(s): {', '.join(sorted(set(placeholders)))}",
            )
        )

    if 'id="fd-canvas"' not in text and "id='fd-canvas'" not in text:
        findings.append(Finding("error", "fd-canvas", "missing #fd-canvas"))
    if 'id="fd-edges"' not in text and "id='fd-edges'" not in text:
        findings.append(Finding("error", "fd-edges", "missing #fd-edges"))

    m = FD_DATA_RE.search(text)
    if not m:
        findings.append(Finding("error", "fd-data", 'missing <script id="fd-data">'))
    else:
        try:
            descriptor = json.loads(m.group(1))
        except json.JSONDecodeError as exc:
            findings.append(Finding("error", "fd-data-json", f"invalid JSON: {exc}"))
        else:
            counts = expect.get("counts", {})
            for key, json_key in (("nodes", "nodes"), ("edges", "edges")):
                expected = counts.get(key)
                if expected is not None:
                    actual = len(descriptor.get(json_key) or [])
                    if actual != expected:
                        findings.append(
                            Finding(
                                "error",
                                f"{key}-count-data",
                                f"fd-data has {actual} {key}, expected {expected}",
                            )
                        )

    for symbol in ("window.__fd", "wireUseCaseUI", "placeZones", "renderNodes"):
        if symbol not in text:
            findings.append(Finding("error", "bundle-symbol", f"missing {symbol} in HTML"))

    if 'name="diagram:engine" content="fd-engine"' not in text:
        findings.append(
            Finding("warn", "diagram-engine-meta", "diagram:engine meta not set to fd-engine")
        )

    return findings


def browser_checks(html_path: Path, expect: dict[str, Any]) -> list[Finding]:
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "playwright",
            "python3",
            str(BROWSER_SCRIPT),
            str(html_path),
            json.dumps(expect),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if proc.returncode not in (0, 1):
        stderr = (proc.stderr or proc.stdout or "").strip()
        return [
            Finding(
                "error",
                "playwright",
                "browser validation failed to run (install: uv run --with playwright python3 -c \"import playwright\")",
                stderr[-500:] if stderr else None,
            )
        ]

    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [
            Finding(
                "error",
                "playwright-output",
                "could not parse browser validator output",
                (proc.stdout or proc.stderr or "")[-500:],
            )
        ]

    return [
        Finding(item["level"], item["code"], item["message"], item.get("detail"))
        for item in raw
    ]


def run_gen_fd(descriptor: Path, output: Path, title: str | None) -> None:
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "gen-fd.py"),
        "--in",
        str(descriptor),
        "--out",
        str(output),
    ]
    if title:
        cmd.extend(["--title", title])
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate fd-engine HTML from gen-fd.py")
    parser.add_argument("--html", type=Path, help="HTML file to validate")
    parser.add_argument("--in", dest="input_path", type=Path, help="Descriptor JSON (gen then validate)")
    parser.add_argument("--out", dest="output_path", type=Path, help="Output HTML when using --in")
    parser.add_argument("--title", default=None, help="Title override for gen-fd.py")
    parser.add_argument(
        "--expect",
        type=Path,
        default=None,
        help="Expectations JSON (default: lyra-stack-v2.expect.json when validating lyra fixture output)",
    )
    parser.add_argument("--static-only", action="store_true", help="Skip Playwright layout checks")
    args = parser.parse_args()

    if args.input_path:
        if not args.output_path:
            print("validate-fd: --out is required with --in", file=sys.stderr)
            sys.exit(2)
        run_gen_fd(args.input_path.resolve(), args.output_path.resolve(), args.title)
        html_path = args.output_path.resolve()
    elif args.html:
        html_path = args.html.resolve()
    else:
        parser.error("provide --html or --in/--out")

    if not html_path.exists():
        print(f"validate-fd: file not found: {html_path}", file=sys.stderr)
        sys.exit(2)

    expect_path = args.expect.resolve() if args.expect else None
    if expect_path is None and args.input_path:
        sibling = args.input_path.resolve().with_suffix(".expect.json")
        if sibling.exists():
            expect_path = sibling
    if expect_path is None and DEFAULT_EXPECT is not None:
        expect_path = DEFAULT_EXPECT

    expect = load_expect(expect_path)

    findings = static_checks(html_path, expect)
    if not args.static_only:
        findings.extend(browser_checks(html_path, expect))

    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    for f in findings:
        print(f.format(), file=sys.stderr)

    if errors:
        print(f"\nvalidate-fd: FAIL — {len(errors)} error(s), {len(warns)} warning(s)", file=sys.stderr)
        sys.exit(1)

    msg = "validate-fd: PASS — all checks ok"
    if warns:
        msg += f" ({len(warns)} warning(s))"
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()