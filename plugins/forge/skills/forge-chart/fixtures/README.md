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

## This issue scope

Infrastructure only. No validation runner executes in CI yet. Fixtures exist today so that:
- regression anchors are authored alongside the prompts that produced them, and
- the runner, when it lands, has a ready corpus to wire up.
