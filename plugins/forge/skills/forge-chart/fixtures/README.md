# forge-chart fixtures

Stable JSON inputs that anchor regression testing for `forge-chart`. Each file describes a single invocation — the prompt, slug, project context — that the skill should be able to render deterministically.

## Schema

```json
{
  "skill": "forge-chart",
  "variant": "<chart kind>",
  "input": {
    "prompt": "<user prompt to the skill>",
    "slug": "<output filename stem>",
    "project": "<target project under ~/.roxabi/forge/>"
  },
  "expected_output_hash": null,
  "notes": "<one line on what this fixture exercises>"
}
```

| Key | Type | Purpose |
|---|---|---|
| `skill` | string | Always `"forge-chart"` for this directory. |
| `variant` | string | Matches one of the chart kinds in `SKILL.md` (fgraph template name, plain-CSS, foreignObject-flexbox, …). |
| `input.prompt` | string | Verbatim user prompt. |
| `input.slug` | string | Output file stem — passed to the skill as the target filename. |
| `input.project` | string | Project scope under `~/.roxabi/forge/<project>/`. |
| `expected_output_hash` | string \| null | **Null in this issue.** Future runners will populate with the SHA-256 of the rendered HTML (whitespace-normalized). |
| `notes` | string | Intent of the fixture — what it exercises or regressions it pins. |

## Hash algorithm (future)

When a fixture runner lands, `expected_output_hash` will be:

```
sha256( render(skill, input) | normalize-whitespace )
```

Normalization collapses runs of whitespace within text nodes and strips trailing newlines — so that cosmetic reformatting doesn't trigger false diffs.

## fd-engine fixtures

| File | Exercises |
|---|---|
| `lyra-stack-v2.json` | Lyra-scale architecture: 26 nodes, 32 edges, 6 use-cases — input for `scripts/gen-fd.py` |

Generate HTML from the fixture:

```bash
python3 scripts/gen-fd.py \
  --in plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.json \
  --out /tmp/lyra-stack-v2-gen.html \
  --title "Lyra — Architecture"
```

Validate layout before shipping (static + Playwright):

```bash
python3 scripts/validate-fd.py \
  --html /tmp/lyra-stack-v2-gen.html \
  --expect plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.expect.json
```

One-shot generate + validate:

```bash
bun run gen-fd:check
# or
python3 scripts/validate-fd.py \
  --in plugins/forge/skills/forge-chart/fixtures/lyra-stack-v2.json \
  --out /tmp/lyra-stack-v2-gen.html \
  --title "Lyra · Architecture"
```

Expectations file: `lyra-stack-v2.expect.json` (node counts, min gaps, canvas bounds).

## CI and deploy gates

| Gate | Command | Browser layout |
|---|---|---|
| CI (PR) | `bun run gen-fd:check` | Full Playwright |
| CI (contract) | `scripts/validate-descriptor.test.sh` | N/A (JSON estimate) |
| Deploy `build.sh` | lyra fixture via `validate-fd.py` | Full when `uv` + Playwright available; else `--static-only` with warning |

`--static-only` skips DOM pair-gap checks defined in `lyra-stack-v2.expect.json` under `layout.*`. Always run `bun run gen-fd:check` before merging fd-engine changes.
