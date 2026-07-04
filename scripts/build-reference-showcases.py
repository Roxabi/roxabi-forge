#!/usr/bin/env python3
"""Build forge reference showcases + craft diagram golden examples."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "forge"
REFS = PLUGIN / "references"
SHOWCASES = REFS / "showcases"
DIAG_EXAMPLES = REFS / "diagrams" / "examples"
CRAFT_JS = (REFS / "diagrams" / "craft-anchors.js").read_text(encoding="utf-8")


def craft_js_safe() -> str:
    """Escape sequences that break HTML script parsing when inlined."""
    return CRAFT_JS.replace("</script>", "<\\/script>")


def read_css(*parts: str) -> str:
    return "\n".join((REFS / p).read_text(encoding="utf-8") for p in parts)


def presentation_css() -> str:
    return read_css(
        "base/reset.css",
        "base/typography.css",
        "aesthetics/roxabi.css",
        "base/explainer-base.css",
        "base/presentation-shell.css",
        "base/composition.css",
    )


def split_css() -> str:
    return read_css(
        "base/reset.css",
        "base/layout.css",
        "base/typography.css",
        "base/components.css",
        "base/explainer-base.css",
        "aesthetics/roxabi.css",
    )


def craft_base_css() -> str:
    return """
    :root {
      --bg: #0d1117; --panel: #13191f; --surface: #161b22;
      --accent: #f0b429; --cyan: #38bdf8; --green: #34d399;
      --text: #f0ede6; --text-muted: #9ca3af; --text-dim: #6b7280;
      --border: #21262d; --border-hi: #30363d;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html.embed-hero, html.embed-hero body { background: transparent; }
    body {
      font-family: 'IBM Plex Sans', sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 40px 20px;
    }
    html.embed-hero body { padding: 12px 8px; min-height: 0; }
    .diagram { position: relative; width: 960px; height: 640px; max-width: 100%; }
    html.embed-hero .diagram {
      transform: scale(min(1, calc((100vw - 32px) / 960)));
      transform-origin: top center;
    }
    .title-block { position: absolute; top: 0; left: 0; right: 0; text-align: center; z-index: 20; }
    .title-block h1 { font-weight: 700; font-size: 2rem; letter-spacing: -0.02em; margin-bottom: 8px; }
    .title-block .subtitle {
      font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem;
      letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-muted);
    }
    .zone-label {
      position: absolute; font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem;
      letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-dim);
      padding: 4px 10px; border: 1px dashed var(--border-hi); border-radius: 4px; z-index: 8;
    }
    .hub {
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -46%);
      width: 188px; height: 188px; background: var(--panel);
      border: 2px solid var(--accent); border-radius: 12px;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      box-shadow: 0 0 48px rgba(240, 180, 41, 0.18); z-index: 12;
    }
    .hub-icon { width: 42px; height: 42px; margin-bottom: 10px; }
    .hub-label { font-weight: 600; font-size: 1.05rem; color: var(--accent); text-align: center; }
    .hub-desc {
      font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; color: var(--text-dim);
      margin-top: 6px; text-align: center; line-height: 1.45; padding: 0 12px;
    }
    .hub-badge {
      position: absolute; top: 8px; right: 8px; font-family: 'IBM Plex Mono', monospace;
      font-size: 0.55rem; color: var(--accent); background: var(--bg);
      border: 1px solid var(--accent); border-radius: 4px; padding: 3px 6px;
    }
    .spoke {
      position: absolute; width: 148px; height: 100px; background: var(--surface);
      border: 1px solid var(--border-hi); border-radius: 8px;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      z-index: 11; transition: border-color 0.2s, transform 0.2s;
    }
    .spoke:hover { border-color: var(--accent); transform: scale(1.02); }
    .spoke.input { border-color: rgba(56, 189, 248, 0.35); }
    .spoke.output { border-color: rgba(52, 211, 153, 0.3); }
    .spoke-icon { width: 24px; height: 24px; margin-bottom: 8px; opacity: 0.9; }
    .spoke-label { font-weight: 500; font-size: 0.84rem; text-align: center; }
    .spoke-desc {
      font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; color: var(--text-dim);
      margin-top: 3px; text-align: center; line-height: 1.35; padding: 0 8px;
    }
    .spoke-chart { top: 128px; left: 56px; }
    .spoke-presentation { top: 128px; right: 56px; }
    .spoke-craft { bottom: 68px; left: 56px; }
    .spoke-serve { bottom: 68px; right: 56px; }
    .spoke-refs {
      top: 50%; left: 28px; transform: translateY(-50%);
      width: 118px; height: 86px;
    }
    .spoke-refs:hover { transform: translateY(-50%) scale(1.02); }
    .spoke-scripts {
      top: 50%; right: 28px; transform: translateY(-50%);
      width: 118px; height: 86px;
    }
    .spoke-scripts:hover { transform: translateY(-50%) scale(1.02); }
    .spoke-prod { top: 118px; left: 120px; width: 160px; }
    .spoke-staging { top: 118px; right: 120px; width: 160px; }
    .spoke-preview { bottom: 88px; left: 50%; transform: translateX(-50%); width: 200px; }
    .spoke-preview:hover { transform: translateX(-50%) scale(1.02); }
    svg.craft-connections {
      position: absolute; inset: 0; width: 100%; height: 100%;
      pointer-events: none; z-index: 6;
    }
    .connection { stroke: var(--border-hi); stroke-width: 2; fill: none; stroke-dasharray: 6 4; }
    .connection.active { stroke: var(--accent); stroke-dasharray: none; opacity: 0.75; }
    .connection.cyan { stroke: var(--cyan); stroke-dasharray: none; opacity: 0.6; }
    .connection.green { stroke: var(--green); stroke-dasharray: none; opacity: 0.65; }
    .connection.blocked { stroke: #ef4444; stroke-dasharray: 4 6; opacity: 0.5; }
    .legend {
      position: absolute; bottom: 10px; left: 0; right: 0;
      display: flex; justify-content: center; gap: 24px;
      font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; color: var(--text-dim); z-index: 20;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-line { width: 22px; height: 2px; }
    .legend-line.solid { background: var(--accent); opacity: 0.75; }
    .legend-line.cyan { background: var(--cyan); opacity: 0.65; }
    .legend-line.green { background: var(--green); opacity: 0.65; }
    .edge-label {
      position: absolute; font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem;
      color: var(--text-dim); background: var(--bg); padding: 2px 7px; border-radius: 4px;
      border: 1px solid var(--border); white-space: nowrap; z-index: 14;
    }
    .rule-badge {
      position: absolute; bottom: 44px; left: 50%; transform: translateX(-50%);
      font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; color: var(--text-dim);
      padding: 5px 12px; border: 1px solid var(--border); border-radius: 4px;
      max-width: 520px; line-height: 1.45; text-align: center; z-index: 20;
    }
    @keyframes flow { to { stroke-dashoffset: -200px; } }
    .connection.flow { animation: flow 20s linear infinite; }
    """


def craft_html(
    *,
    title: str,
    subtitle: str,
    slug: str,
    body_inner: str,
    edges: dict,
    embed_script: bool = True,
) -> str:
    embed = """
  <script>
    (function () {
      if (/[?&]embed=hero/.test(location.search)) {
        document.documentElement.classList.add('embed-hero');
      }
    })();
  </script>"""
    edges_json = json.dumps(edges, indent=2)
    js_block = f"\n  <script>\n{craft_js_safe()}\n  </script>" if embed_script else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="{title}">
  <meta name="diagram:category" content="architecture">
  <meta name="diagram:color" content="#f0b429">
  <title>{title}</title>{embed}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>{craft_base_css()}</style>
</head>
<body>
  <div class="diagram" data-slug="{slug}" data-canvas-width="960" data-canvas-height="640">
{body_inner}
  </div>
  <script type="application/json" id="craft-edges">
{edges_json}
  </script>{js_block}
</body>
</html>
"""


def build_craft_hub_spoke() -> None:
    body = """
    <div class="title-block">
      <h1>Forge Plugin Topology</h1>
      <div class="subtitle">Skills · References · Scripts · Runtime</div>
    </div>
    <div class="zone-label" style="top:86px;left:8px">authoring</div>
    <div class="zone-label" style="top:86px;right:8px">runtime</div>
    <svg class="craft-connections" aria-hidden="true"></svg>
    <div class="edge-label" style="left:248px;top:198px">descriptor JSON</div>
    <div class="edge-label" style="right:248px;top:198px">scroll + iframe</div>
    <div class="edge-label" style="left:188px;top:50%;transform:translateY(-130%)">CSS SSoT</div>
    <div class="edge-label" style="right:188px;top:50%;transform:translateY(-130%)">validate-*</div>
    <div class="hub" data-anchor="hub">
      <div class="hub-badge">SSoT</div>
      <svg class="hub-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <circle cx="24" cy="24" r="18" stroke="var(--accent)" stroke-width="2"/>
        <path d="M24 8v32M8 24h32" stroke="var(--accent)" stroke-width="2"/>
        <circle cx="24" cy="24" r="6" fill="var(--accent)"/>
      </svg>
      <div class="hub-label">Roxabi Forge</div>
      <div class="hub-desc">~/.roxabi/forge<br>serve.py · manifest</div>
    </div>
    <div class="spoke spoke-chart input" data-anchor="chart">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 17V11M12 17V7M17 17v-5"/></svg>
      <div class="spoke-label">forge-chart</div>
      <div class="spoke-desc">fd-engine · gen-fd.py</div>
    </div>
    <div class="spoke spoke-presentation input" data-anchor="presentation">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2"><path d="M4 6h16M4 12h10M4 18h14"/></svg>
      <div class="spoke-label">forge-presentation</div>
      <div class="spoke-desc">scroll · craft iframe</div>
    </div>
    <div class="spoke spoke-craft output" data-anchor="craft">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>
      <div class="spoke-label">craft-anchors</div>
      <div class="spoke-desc">data-anchor · edges JSON</div>
    </div>
    <div class="spoke spoke-serve output" data-anchor="serve">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
      <div class="spoke-label">serve.py</div>
      <div class="spoke-desc">file:// · gallery UI</div>
    </div>
    <div class="spoke spoke-refs input" data-anchor="refs">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      <div class="spoke-label">references/</div>
      <div class="spoke-desc">aesthetics · templates</div>
    </div>
    <div class="spoke spoke-scripts output" data-anchor="scripts">
      <svg class="spoke-icon" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
      <div class="spoke-label">scripts/</div>
      <div class="spoke-desc">check · validate</div>
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-line solid"></div><span>skill output</span></div>
      <div class="legend-item"><div class="legend-line cyan"></div><span>authoring</span></div>
      <div class="legend-item"><div class="legend-line green"></div><span>runtime</span></div>
    </div>
    <div class="rule-badge">Golden craft bar: zone labels · legend · edge labels · craft-anchors paths</div>"""
    edges = {
        "viewBox": "0 0 960 640",
        "edges": [
            {"from": "chart", "to": "hub", "class": "connection active", "curve": "q"},
            {"from": "presentation", "to": "hub", "class": "connection cyan", "curve": "q"},
            {"from": "refs", "to": "hub", "class": "connection cyan", "curve": "q"},
            {"from": "hub", "to": "craft", "class": "connection active", "curve": "q"},
            {"from": "hub", "to": "serve", "class": "connection green", "curve": "q"},
            {"from": "hub", "to": "scripts", "class": "connection green", "curve": "q"},
        ],
    }
    out = craft_html(
        title="Forge Plugin Topology",
        subtitle="Skills · References · Scripts · Runtime",
        slug="craft-hub-spoke.html",
        body_inner=body,
        edges=edges,
    )
    DIAG_EXAMPLES.mkdir(parents=True, exist_ok=True)
    (DIAG_EXAMPLES / "craft-hub-spoke.html").write_text(out, encoding="utf-8")
    print("wrote craft-hub-spoke.html")


def build_craft_deploy_flow() -> None:
    body = """
    <div class="title-block">
      <h1>Deploy Promote Flow</h1>
      <div class="subtitle">main → staging → preview · curve h</div>
    </div>
    <svg class="craft-connections" aria-hidden="true"></svg>
    <div class="edge-label" style="left:50%;top:268px;transform:translateX(-50%)">merge → auto-deploy</div>
    <div class="edge-label" style="left:50%;bottom:168px;transform:translateX(-50%)">promote · curve h</div>
    <div class="hub" data-anchor="hub" style="width:160px;height:120px;transform:translate(-50%,-30%)">
      <div class="hub-label">CI Gate</div>
      <div class="hub-desc">validate-fd · check-craft</div>
    </div>
    <div class="spoke spoke-prod input" data-anchor="prod">
      <div class="spoke-label">production</div>
      <div class="spoke-desc">main branch</div>
    </div>
    <div class="spoke spoke-staging input" data-anchor="staging">
      <div class="spoke-label">staging</div>
      <div class="spoke-desc">integration</div>
    </div>
    <div class="spoke spoke-preview output" data-anchor="preview">
      <div class="spoke-label">preview</div>
      <div class="spoke-desc">feat/* · PR</div>
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-line solid"></div><span>active path</span></div>
      <div class="legend-item"><div class="legend-line green"></div><span>promote h-curve</span></div>
    </div>"""
    edges = {
        "viewBox": "0 0 960 640",
        "edges": [
            {"from": "prod", "to": "hub", "class": "connection active", "curve": "q"},
            {"from": "staging", "to": "hub", "class": "connection cyan", "curve": "q"},
            {"from": "hub", "to": "preview", "class": "connection green", "curve": "q"},
            {"from": "prod", "to": "staging", "class": "connection green flow", "curve": "h", "y": 478},
        ],
    }
    out = craft_html(
        title="Deploy Promote Flow",
        subtitle="main → staging → preview",
        slug="craft-deploy-flow.html",
        body_inner=body,
        edges=edges,
    )
    (DIAG_EXAMPLES / "craft-deploy-flow.html").write_text(out, encoding="utf-8")
    print("wrote craft-deploy-flow.html")


def build_showcase_presentation() -> None:
    css = presentation_css()
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge Presentation — Reference Showcase">
  <meta name="diagram:date" content="2026-07-04">
  <meta name="diagram:category" content="demo">
  <meta name="diagram:cat-label" content="Showcase">
  <meta name="diagram:color" content="gold">
  <meta name="diagram:badges" content="latest">
  <title>Forge Presentation — Reference Showcase</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Inter:wght@400;500;600&family=Space+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>{css}</style>
  <style>
    #section-craft-hub .diagram-frame,
    #section-craft-deploy .diagram-frame {{
      border: none; background: transparent; width: 100%; display: block;
    }}
    .method {{ margin-top: 2rem; padding: 1.25rem; border: 1px solid var(--border); border-radius: 8px; }}
    .method dt {{ font-family: var(--mono, monospace); font-size: 0.72rem; color: var(--accent); }}
    .method dd {{ margin: 0 0 0.75rem; color: var(--text-muted); font-size: 0.9rem; }}
  </style>
</head>
<body>

<section class="hero reveal">
  <div class="hero-left">
    <div class="eyebrow">forge-presentation · reference</div>
    <div class="hero-wordmark">Composition<sup>×</sup></div>
    <div class="hero-release">2026-07-04 · roxabi aesthetic</div>
    <div class="hero-tagline">Scroll narrative + craft diagram iframes — the canonical integration pattern.</div>
  </div>
  <div class="hero-scroll">↓ scroll</div>
</section>

<section id="section-1" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 01</div>
    <div>
      <div class="eyebrow">Intent</div>
      <div class="section-title">Presentation owns prose — diagrams own geometry</div>
      <div class="section-sub">Never copy craft CSS into the presentation shell.</div>
    </div>
  </div>
  <p>Premium hub-spoke canvases live in sibling <code>diagrams/*.html</code> files and embed via <code>&lt;iframe class="diagram-frame"&gt;</code>. Relative paths keep <code>file://</code> offline safety.</p>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-val">2</div><div class="kpi-lbl">craft iframes</div></div>
    <div class="kpi"><div class="kpi-val">6</div><div class="kpi-lbl">CSS layers inlined</div></div>
    <div class="kpi"><div class="kpi-val">0</div><div class="kpi-lbl">hand-coded paths</div></div>
  </div>
</section>

<section id="section-craft-hub" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 02</div>
    <div>
      <div class="eyebrow">craft-diagram</div>
      <div class="section-sub">Golden hub-spoke — <code>craft-hub-spoke.html</code></div>
    </div>
  </div>
  <figure class="diagram-embed arch-wrap">
    <iframe class="diagram-frame" src="../diagrams/examples/craft-hub-spoke.html?embed=hero" data-height="720" title="Forge Plugin Topology" loading="lazy"></iframe>
  </figure>
</section>

<section id="section-2" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 03</div>
    <div>
      <div class="eyebrow">panel</div>
      <div class="section-title">Tables use panel-wrap — not bare tbl-wrap</div>
    </div>
  </div>
  <div class="panel-wrap reveal">
    <div class="panel-head">
      <span class="panel-eyebrow">composition primitives</span>
      <span class="panel-title">Block taxonomy</span>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>Block</th><th>When</th><th>Reveal</th></tr></thead>
        <tbody>
          <tr><td><code>diagram-embed</code></td><td>Craft canvas SSoT</td><td>Parent only</td></tr>
          <tr><td><code>panel-wrap</code></td><td>Tables + swimlanes</td><td>Stagger children</td></tr>
          <tr><td><code>arch-wrap</code></td><td>Light pipelines ≤7 steps</td><td>Once on parent</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="section-craft-deploy" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 04</div>
    <div>
      <div class="eyebrow">craft-diagram</div>
      <div class="section-sub">Promote flow — <code>curve: "h"</code> in craft-edges</div>
    </div>
  </div>
  <figure class="diagram-embed arch-wrap">
    <iframe class="diagram-frame" src="../diagrams/examples/craft-deploy-flow.html?embed=hero" data-height="680" title="Deploy Promote Flow" loading="lazy"></iframe>
  </figure>
</section>

<section id="section-3" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 05</div>
    <div>
      <div class="eyebrow">caveats</div>
      <div class="section-title">Integration guardrails</div>
    </div>
  </div>
  <div class="caveat-grid">
    <div class="caveat-card warn"><strong>No duplicate titles</strong><p>Title lives inside the diagram — no figcaption on iframe.</p></div>
    <div class="caveat-card ok"><strong>forge-diagram-resize</strong><p>postMessage type must match presentation listener.</p></div>
  </div>
</section>

<section id="section-4" class="reveal">
  <div class="section-h">
    <div class="section-n">§ 06</div>
    <div>
      <div class="eyebrow">method</div>
      <div class="section-title">How this showcase was built</div>
    </div>
  </div>
  <dl class="method">
    <dt>Golden craft</dt><dd><code>references/diagrams/examples/craft-hub-spoke.html</code></dd>
    <dt>Starter</dt><dd><code>references/diagrams/craft-diagram-starter.html</code> (copy base)</dd>
    <dt>Validation</dt><dd><code>check-craft-diagram.py</code> + <code>check-composition.py</code></dd>
  </dl>
</section>

<footer>
  <div class="foot-brand">Forge Presentation</div>
  <div class="foot-date">— reference showcase</div>
  <div class="foot-meta">roxabi · composition-contract.md</div>
</footer>

<script>
  const obs = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{ e.target.classList.add('visible'); obs.unobserve(e.target); }}
    }});
  }}, {{ threshold: 0.12 }});
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

  document.querySelectorAll('.diagram-frame').forEach(function (iframe) {{
    var h = parseInt(iframe.dataset.height || '400', 10);
    iframe.style.height = h + 'px';
  }});
  window.addEventListener('message', function (e) {{
    if (!e.data || e.data.type !== 'forge-diagram-resize') return;
    document.querySelectorAll('.diagram-frame').forEach(function (iframe) {{
      if (iframe.src && iframe.src.includes(e.data.id)) {{
        iframe.style.height = Math.max(e.data.height, parseInt(iframe.dataset.height || '200', 10)) + 'px';
      }}
    }});
  }});
</script>
</body>
</html>"""
    SHOWCASES.mkdir(parents=True, exist_ok=True)
    (SHOWCASES / "showcase-presentation.html").write_text(html, encoding="utf-8")
    print("wrote showcase-presentation.html")


def tab_shell_css_extra() -> str:
    return """
    .topnav { display:flex; align-items:center; justify-content:space-between; gap:1rem;
      padding:0.75rem 1.5rem; border-bottom:1px solid var(--border); position:sticky; top:0;
      background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); z-index:50; }
    .tabs { display:flex; gap:0.35rem; flex-wrap:wrap; }
    .tab-btn { background:transparent; border:1px solid var(--border); color:var(--text-muted);
      padding:0.4rem 0.85rem; border-radius:6px; font-size:0.82rem; cursor:pointer; }
    .tab-btn.active, .tab-btn[aria-selected="true"] { border-color:var(--accent); color:var(--accent); background:var(--accent-dim); }
    .panel { display:none; padding:1.5rem; max-width:1100px; margin:0 auto; }
    .panel.active { display:block; }
    .epic-hero { padding:2rem 1.5rem 1rem; max-width:1100px; margin:0 auto; }
    .epic-number { font-family:var(--mono, monospace); color:var(--accent); font-size:0.85rem; }
    .epic-goal { color:var(--text-muted); margin-top:0.5rem; max-width:60ch; }
    .status { font-family:var(--mono, monospace); font-size:0.68rem; padding:2px 8px; border-radius:4px; }
    .status.done { background:rgba(52,211,153,0.15); color:#34d399; }
    .status.wip { background:rgba(240,180,41,0.15); color:var(--accent); }
    .status.todo { background:rgba(107,114,128,0.2); color:var(--text-dim); }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; margin:1rem 0; }
    .card.accent { border-color:color-mix(in srgb, var(--accent) 35%, var(--border)); }
    .theme-btn { background:var(--surface); border:1px solid var(--border); color:var(--text-muted);
      padding:0.35rem 0.7rem; border-radius:6px; cursor:pointer; font-size:0.78rem; }
    """


def build_showcase_epic() -> None:
    css = split_css() + tab_shell_css_extra()
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="#42 — Craft diagram references">
  <meta name="diagram:date" content="2026-07-04">
  <meta name="diagram:category" content="epic">
  <meta name="diagram:issue" content="42">
  <meta name="diagram:color" content="gold">
  <title>#42 — Craft diagram references</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>{css}</style>
</head>
<body>
  <div class="epic-hero">
    <div class="epic-number">Issue #42</div>
    <h1>Craft diagram golden references</h1>
    <p class="epic-goal">Ship plugin-level HQ examples for forge-presentation craft iframe integration and craft-anchors authoring.</p>
  </div>
  <nav class="topnav">
    <div class="tabs" role="tablist">
      <button class="tab-btn active" data-tab="overview" role="tab" aria-selected="true">overview</button>
      <button class="tab-btn" data-tab="breakdown" role="tab">breakdown</button>
      <button class="tab-btn" data-tab="deps" role="tab">deps</button>
      <button class="tab-btn" data-tab="criteria" role="tab">criteria</button>
    </div>
    <button class="theme-btn" id="theme-toggle">◑ theme</button>
  </nav>
  <div class="panel active" data-panel="overview" role="tabpanel">
    <div class="cards">
      <div class="card accent"><h3>craft-hub-spoke</h3><p>Golden hub-spoke with zone labels, legend, 6 anchors.</p></div>
      <div class="card accent"><h3>showcase-presentation</h3><p>Scroll doc embedding 2 craft iframes + panel-wrap table.</p></div>
      <div class="card accent"><h3>check scripts</h3><p>check-craft-diagram.py + check-composition.py gates.</p></div>
    </div>
  </div>
  <div class="panel" data-panel="breakdown" role="tabpanel">
    <div class="table-wrap"><table>
      <thead><tr><th>Task</th><th>Owner</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>craft-hub-spoke.html golden</td><td>forge</td><td><span class="status done">done</span></td></tr>
        <tr><td>showcase-presentation.html</td><td>forge</td><td><span class="status done">done</span></td></tr>
        <tr><td>showcase-index.html</td><td>forge</td><td><span class="status done">done</span></td></tr>
        <tr><td>Migrate legacy diagrams</td><td>projects</td><td><span class="status todo">todo</span></td></tr>
      </tbody>
    </table></div>
  </div>
  <div class="panel" data-panel="deps" role="tabpanel">
    <div class="arch-wrap">
      <div class="arch-pipeline">
        <span class="arch-node">composition-contract</span><span class="arch-arrow">→</span>
        <span class="arch-node">craft-anchors.js</span><span class="arch-arrow">→</span>
        <span class="arch-node">craft examples</span><span class="arch-arrow">→</span>
        <span class="arch-node">showcase-presentation</span>
      </div>
    </div>
  </div>
  <div class="panel" data-panel="criteria" role="tabpanel">
    <div class="table-wrap"><table>
      <thead><tr><th>Criterion</th><th>Gate</th></tr></thead>
      <tbody>
        <tr><td>craft diagrams pass check-craft-diagram.py</td><td>exit 0</td></tr>
        <tr><td>presentation passes check-composition.py</td><td>exit 0</td></tr>
        <tr><td>SKILL.md points to golden paths</td><td>documented</td></tr>
        <tr><td>showcase-index lists all artifact types</td><td>31+ entries</td></tr>
      </tbody>
    </table></div>
  </div>
  <script>
    document.querySelectorAll('.tab-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => {{ b.classList.remove('active'); b.setAttribute('aria-selected','false'); }});
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active'); btn.setAttribute('aria-selected','true');
        document.querySelector('[data-panel="'+btn.dataset.tab+'"]').classList.add('active');
      }});
    }});
    document.getElementById('theme-toggle').addEventListener('click', () => {{
      const html = document.documentElement;
      html.dataset.theme = html.dataset.theme === 'light' ? 'dark' : 'light';
    }});
  </script>
</body>
</html>"""
    (SHOWCASES / "showcase-epic.html").write_text(html, encoding="utf-8")
    print("wrote showcase-epic.html")


def build_showcase_guide() -> None:
    css = split_css() + tab_shell_css_extra()
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge References — Author Guide">
  <meta name="diagram:date" content="2026-07-04">
  <meta name="diagram:category" content="guide">
  <meta name="diagram:color" content="gold">
  <title>Forge References — Author Guide</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>{css}</style>
</head>
<body>
  <header class="hero elevated" style="margin:0;border-radius:0;border-left:none">
    <div class="hero-eyebrow">forge-guide · reference</div>
    <h1>Authoring HQ forge artifacts</h1>
    <p>Multi-tab guide pattern — overview, architecture, workflow, QA.</p>
    <div class="stat-grid" style="margin-top:1.25rem">
      <div class="stat"><div class="stat-val">7</div><div class="stat-lbl">skills</div></div>
      <div class="stat"><div class="stat-val">4</div><div class="stat-lbl">golden diagrams</div></div>
      <div class="stat"><div class="stat-val">2</div><div class="stat-lbl">check scripts</div></div>
    </div>
  </header>
  <nav class="topnav">
    <div class="tabs" role="tablist">
      <button class="tab-btn active" data-tab="overview" role="tab" aria-selected="true">overview</button>
      <button class="tab-btn" data-tab="architecture" role="tab">architecture</button>
      <button class="tab-btn" data-tab="workflow" role="tab">workflow</button>
      <button class="tab-btn" data-tab="reference" role="tab">reference</button>
    </div>
    <button class="theme-btn" id="theme-toggle">◑ theme</button>
  </nav>
  <div class="panel active" data-panel="overview"><p>Start from the golden example for your skill type. Never improvise craft geometry without <code>craft-anchors</code>.</p></div>
  <div class="panel" data-panel="architecture">
    <figure class="diagram-embed arch-wrap">
      <iframe class="diagram-frame" src="../diagrams/examples/craft-hub-spoke.html?embed=hero" data-height="700" style="width:100%;border:none;background:transparent" title="Forge topology"></iframe>
    </figure>
  </div>
  <div class="panel" data-panel="workflow">
    <div class="phases">
      <div class="phase-card"><div class="phase-n">1</div><div class="phase-t">Copy starter</div><div class="phase-d">craft-diagram-starter.html</div></div>
      <div class="phase-card"><div class="phase-n">2</div><div class="phase-t">Anchor nodes</div><div class="phase-d">data-anchor + CSS only</div></div>
      <div class="phase-card"><div class="phase-n">3</div><div class="phase-t">Validate</div><div class="phase-d">check-craft + QA checklist</div></div>
    </div>
  </div>
  <div class="panel" data-panel="reference">
    <div class="table-wrap"><table>
      <thead><tr><th>Path</th><th>Purpose</th></tr></thead>
      <tbody>
        <tr><td><code>diagrams/examples/craft-hub-spoke.html</code></td><td>Golden craft hub-spoke</td></tr>
        <tr><td><code>showcases/showcase-presentation.html</code></td><td>Scroll + iframe integration</td></tr>
        <tr><td><code>graph-templates/examples/fd-architecture.html</code></td><td>Golden fd-engine</td></tr>
      </tbody>
    </table></div>
  </div>
  <script>
    document.querySelectorAll('.tab-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => {{ b.classList.remove('active'); b.setAttribute('aria-selected','false'); }});
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active'); btn.setAttribute('aria-selected','true');
        document.querySelector('[data-panel="'+btn.dataset.tab+'"]').classList.add('active');
      }});
    }});
    document.getElementById('theme-toggle').addEventListener('click', () => {{
      const html = document.documentElement;
      html.dataset.theme = html.dataset.theme === 'light' ? 'dark' : 'light';
    }});
  </script>
</body>
</html>"""
    (SHOWCASES / "showcase-guide.html").write_text(html, encoding="utf-8")
    print("wrote showcase-guide.html")


MINIMAL_SLIDE_JS = """
class SlideEngine {
  constructor(deck) {
    this.deck = deck || document.querySelector('.deck');
    this.slides = [...this.deck.querySelectorAll('.slide')];
    this.total = this.slides.length;
    this.current = 0;
    this.buildChrome();
    this.bindEvents();
    this.observe();
    this.update();
  }
  buildChrome() {
    this.bar = Object.assign(document.createElement('div'), { className: 'deck-progress' });
    document.body.appendChild(this.bar);
    const dots = Object.assign(document.createElement('div'), { className: 'deck-dots' });
    this.slides.forEach((_, i) => {
      const d = Object.assign(document.createElement('button'), { className: 'deck-dot' });
      d.type = 'button';
      d.setAttribute('aria-label', 'Go to slide ' + (i + 1));
      d.addEventListener('click', () => this.goTo(i));
      dots.appendChild(d);
    });
    document.body.appendChild(dots);
    this.dots = [...dots.children];
    this.counter = Object.assign(document.createElement('div'), { className: 'deck-counter' });
    document.body.appendChild(this.counter);
  }
  bindEvents() {
    document.addEventListener('keydown', (e) => {
      if (e.target.closest('input,textarea,[contenteditable]')) return;
      const k = e.key;
      if (['ArrowDown','ArrowRight',' ','PageDown'].includes(k)) { e.preventDefault(); this.next(); }
      else if (['ArrowUp','ArrowLeft','PageUp'].includes(k)) { e.preventDefault(); this.prev(); }
      else if (k === 'Home') { e.preventDefault(); this.goTo(0); }
      else if (k === 'End') { e.preventDefault(); this.goTo(this.total - 1); }
    });
  }
  observe() {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          this.current = this.slides.indexOf(entry.target);
          this.update();
        }
      });
    }, { threshold: 0.5 });
    this.slides.forEach((s) => obs.observe(s));
  }
  goTo(i) { this.slides[Math.max(0, Math.min(i, this.total - 1))].scrollIntoView({ behavior: 'smooth' }); }
  next() { if (this.current < this.total - 1) this.goTo(this.current + 1); }
  prev() { if (this.current > 0) this.goTo(this.current - 1); }
  update() {
    const pct = ((this.current + 1) / this.total) * 100;
    this.bar.style.width = pct + '%';
    this.counter.textContent = (this.current + 1) + ' / ' + this.total;
    this.dots.forEach((d, i) => d.classList.toggle('active', i === this.current));
  }
}
document.documentElement.classList.add('deck-body');
new SlideEngine(document.getElementById('deck'));
"""


def build_showcase_slides() -> None:
    slide_css = read_css(
        "base/reset.css",
        "base/typography.css",
        "aesthetics/roxabi.css",
        "slide-templates/slide-deck-base.css",
    )
    slide_js = MINIMAL_SLIDE_JS
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge Slides — Reference Showcase">
  <meta name="diagram:date" content="2026-07-04">
  <meta name="diagram:category" content="demo">
  <meta name="diagram:color" content="gold">
  <title>Forge Slides — Reference Showcase</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Inter:wght@400;500;600&family=Space+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>{slide_css}</style>
</head>
<body class="deck-body">
  <div class="deck" id="deck">
    <section class="slide slide--title" id="slide-1">
      <div class="slide-eyebrow">forge-slides · reference</div>
      <h1>Scroll-snap<br>presentations</h1>
      <p class="slide-sub">roxabi aesthetic · 7 core slide types</p>
    </section>
    <section class="slide slide--section" id="slide-2">
      <div class="section-num">§ 01</div>
      <h2>Context</h2>
    </section>
    <section class="slide slide--content" id="slide-3">
      <h2>When to use slides vs scroll</h2>
      <ul>
        <li>Slides: presenter-led, keyboard nav, one idea per viewport</li>
        <li>Presentation: continuous read, deep sections, iframe diagrams</li>
        <li>Chart: single diagram artifact</li>
      </ul>
    </section>
    <section class="slide slide--comparison" id="slide-4">
      <h2>Output modes</h2>
      <div class="compare-grid">
        <div class="compare-col"><h3>forge-slides</h3><p>Scroll-snap deck · slide-deck-base.js</p></div>
        <div class="compare-col"><h3>forge-presentation</h3><p>Long-form scroll · explainer-base.css</p></div>
      </div>
    </section>
    <section class="slide slide--content" id="slide-5">
      <h2>Golden references</h2>
      <ul>
        <li><code>showcase-slides.html</code> — this file</li>
        <li><code>showcase-presentation.html</code> — craft iframes</li>
        <li><code>fd-architecture.html</code> — fd-engine bar</li>
      </ul>
    </section>
    <section class="slide slide--diagram" id="slide-6">
      <h2>Craft golden</h2>
      <p class="slide-sub">Embed craft diagrams in slides sparingly — prefer chart skill for single visuals.</p>
    </section>
    <section class="slide slide--closing" id="slide-7">
      <h2>Forge references</h2>
      <p>2026-07-04 · roxabi</p>
    </section>
  </div>
  <div id="deck-progress"></div>
  <div id="deck-dots"></div>
  <script>
{slide_js}
  </script>
</body>
</html>"""
    (SHOWCASES / "showcase-slides.html").write_text(html, encoding="utf-8")
    print("wrote showcase-slides.html")


def build_showcase_gallery() -> None:
    gallery_css = (REFS / "gallery-templates" / "gallery-base.css").read_text(encoding="utf-8")  # SSoT: gallery-templates/
    items = [
        ("fd-architecture", "fd-engine", "../graph-templates/examples/fd-architecture.html"),
        ("craft-hub", "craft", "../diagrams/examples/craft-hub-spoke.html"),
        ("showcase-chart", "chart", "showcase-chart.html"),
        ("showcase-presentation", "presentation", "showcase-presentation.html"),
        ("system-architecture", "fgraph", "../graph-templates/examples/system-architecture.html"),
        ("craft-deploy", "craft", "../diagrams/examples/craft-deploy-flow.html"),
    ]
    cards = []
    for i, (name, batch, href) in enumerate(items, 1):
        cards.append(f"""
    <a class="img-card" href="{href}" data-batch="{batch}" data-name="{name}">
      <div class="badge-top">{batch}</div>
      <div style="aspect-ratio:1;background:linear-gradient(135deg,#13191f,#1a2332);display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:0.7rem;color:var(--accent);padding:1rem;text-align:center">{name}</div>
      <div class="info"><div class="num">#{i:02d}</div><div class="lbl">{name}</div></div>
    </a>""")
    cards_html = "\n".join(cards)
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge Reference Gallery Showcase">
  <meta name="diagram:date" content="2026-07-04">
  <meta name="diagram:category" content="gallery">
  <meta name="diagram:color" content="#f0b429">
  <title>Forge Reference Gallery Showcase</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{ --accent:#f0b429; --accent-dim:rgba(240,180,41,0.12); }}
    {gallery_css}
    .layout {{ max-width:1100px; margin:0 auto; padding:24px 20px 64px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:8px; }}
    .img-card {{ text-decoration:none; color:inherit; }}
    .batch-bar {{ display:flex; flex-wrap:wrap; gap:6px; margin:12px 0; }}
    .batch-btn {{ background:var(--surface); border:1px solid var(--border); border-radius:6px; color:var(--text-dim); cursor:pointer; font-family:var(--mono); font-size:.65rem; padding:5px 12px; }}
    .batch-btn.active {{ border-color:var(--accent); color:var(--accent); background:var(--accent-dim); }}
    .img-card.hidden {{ display:none; }}
  </style>
</head>
<body>
<div class="layout">
  <div class="header">
    <div class="header-left">
      <div class="header-title">Forge Reference Gallery</div>
      <div class="header-sub">forge-gallery showcase · {len(items)} golden artifacts</div>
    </div>
    <div class="stats" id="stats">{len(items)} / {len(items)} visible</div>
  </div>
  <div class="batch-bar" id="filters">
    <button class="batch-btn active" data-batch="all">all</button>
    <button class="batch-btn" data-batch="craft">craft</button>
    <button class="batch-btn" data-batch="fd-engine">fd-engine</button>
    <button class="batch-btn" data-batch="fgraph">fgraph</button>
    <button class="batch-btn" data-batch="chart">chart</button>
    <button class="batch-btn" data-batch="presentation">presentation</button>
  </div>
  <div class="grid" id="grid">{cards_html}
  </div>
</div>
<script>
  const cards = document.querySelectorAll('.img-card');
  const stats = document.getElementById('stats');
  document.getElementById('filters').addEventListener('click', e => {{
    const btn = e.target.closest('.batch-btn');
    if (!btn) return;
    document.querySelectorAll('.batch-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const batch = btn.dataset.batch;
    let visible = 0;
    cards.forEach(c => {{
      const show = batch === 'all' || c.dataset.batch === batch;
      c.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    stats.textContent = visible + ' / ' + cards.length + ' visible';
  }});
</script>
</body>
</html>"""
    (SHOWCASES / "showcase-gallery.html").write_text(html, encoding="utf-8")
    print("wrote showcase-gallery.html")


def build_showcase_md() -> None:
    md = """# Forge References

HQ golden examples shipped with the forge plugin.

## Craft diagrams

- `diagrams/examples/craft-hub-spoke.html` — hub-spoke golden
- `diagrams/examples/craft-deploy-flow.html` — promote flow (`curve: h`)

## Showcases

| Skill | File |
|-------|------|
| forge-chart | `showcases/showcase-chart.html` |
| forge-presentation | `showcases/showcase-presentation.html` |
| forge-epic | `showcases/showcase-epic.html` |
| forge-guide | `showcases/showcase-guide.html` |
| forge-slides | `showcases/showcase-slides.html` |
| forge-gallery | `showcases/showcase-gallery.html` |

## Validation

```bash
python3 ~/.roxabi/forge/scripts/check-craft-diagram.py --dir references/diagrams/examples --check
python3 ~/.roxabi/forge/scripts/check-composition.py -p references/showcases/showcase-presentation.html --check
```

> Blockquote: render-as-is — forge-md does not rewrite content.
"""
    (SHOWCASES / "showcase-sample.md").write_text(md, encoding="utf-8")
    body = "".join(
        f"<{'h' + str(min(3, line.count('#') if line.startswith('#') else 1))}>{line.lstrip('# ')}</{'h' + str(min(3, line.count('#') if line.startswith('#') else 1))}>\n"
        if line.startswith("#")
        else (f"<pre><code>{line}</code></pre>\n" if line.startswith("```") else f"<p>{line}</p>\n" if line.strip() and not line.startswith("|") and not line.startswith("-") and not line.startswith(">") else "")
        for line in md.splitlines()
    )
    parts: list[str] = []
    in_code = False
    in_table = False
    table_has_thead = False
    in_list = False

    def close_table() -> None:
        nonlocal in_table, table_has_thead
        if in_table:
            parts.append("</tbody></table></div>")
            in_table = False
            table_has_thead = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for line in md.splitlines():
        if line.startswith("```"):
            close_table()
            close_list()
            in_code = not in_code
            parts.append("<pre><code>" if in_code else "</code></pre>")
            continue
        if in_code:
            parts.append(line + "\n")
            continue
        if line.startswith("# "):
            close_table()
            close_list()
            parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            close_table()
            close_list()
            parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            close_table()
            close_list()
            parts.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("> "):
            close_table()
            close_list()
            parts.append(f"<blockquote><p>{line[2:]}</p></blockquote>")
        elif line.startswith("|"):
            close_list()
            if not in_table:
                parts.append('<div class="table-wrap"><table>')
                in_table = True
                table_has_thead = False
            if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) <= {""}:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not table_has_thead:
                parts.append(
                    "<thead><tr>"
                    + "".join(f"<th>{c}</th>" for c in cells)
                    + "</tr></thead><tbody>"
                )
                table_has_thead = True
            else:
                parts.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        elif line.startswith("- "):
            close_table()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{line[2:]}</li>")
        elif not line.strip():
            close_table()
            close_list()
            parts.append("")
        else:
            close_table()
            close_list()
            parts.append(f"<p>{line}</p>")
    close_table()
    close_list()
    content = "\n".join(parts)
    css = split_css()
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge References (md preview)">
  <meta name="diagram:category" content="docs">
  <title>Forge References — forge-md preview</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono&display=swap" rel="stylesheet">
  <style>
    {css}
    .preview-banner {{ position:sticky; top:0; z-index:10; background:var(--accent-dim); border-bottom:1px solid var(--accent);
      padding:0.5rem 1rem; font-family:var(--mono,monospace); font-size:0.72rem; color:var(--accent); }}
    main {{ max-width:760px; margin:0 auto; padding:2rem 1.5rem 4rem; }}
  </style>
</head>
<body>
  <div class="preview-banner">rendered by forge-md · source: showcase-sample.md</div>
  <main>{content}</main>
</body>
</html>"""
    (SHOWCASES / "showcase-md.html").write_text(html, encoding="utf-8")
    print("wrote showcase-md.html + showcase-sample.md")


# Catalog for showcase-index.html — paths relative to references/
SHOWCASE_CATALOG: list[dict] = [
    {
        "id": "skills",
        "title": "Skill outputs",
        "subtitle": "Golden HTML per forge skill — canonical structure + aesthetic",
        "filter": "skill",
        "items": [
            {"title": "forge-chart", "badge": "skill", "href": "showcases/showcase-chart.html", "desc": "fd-engine premium pipeline demo", "tags": ["chart", "fd-engine"]},
            {"title": "forge-presentation", "badge": "skill", "href": "showcases/showcase-presentation.html", "desc": "Scroll doc + 2 craft iframes + panel-wrap", "tags": ["presentation", "craft"]},
            {"title": "forge-epic", "badge": "skill", "href": "showcases/showcase-epic.html", "desc": "Issue-linked tabs: overview · breakdown · deps · criteria", "tags": ["epic", "tabs"]},
            {"title": "forge-guide", "badge": "skill", "href": "showcases/showcase-guide.html", "desc": "Multi-tab guide + craft iframe embed", "tags": ["guide", "tabs"]},
            {"title": "forge-slides", "badge": "skill", "href": "showcases/showcase-slides.html", "desc": "Scroll-snap deck · 7 slide types", "tags": ["slides"]},
            {"title": "forge-gallery", "badge": "skill", "href": "showcases/showcase-gallery.html", "desc": "Filterable reference gallery UI", "tags": ["gallery"]},
            {"title": "forge-md", "badge": "skill", "href": "showcases/showcase-md.html", "desc": "Markdown render-as-is preview", "tags": ["md", "docs"]},
        ],
    },
    {
        "id": "craft",
        "title": "Craft diagrams",
        "subtitle": "Hand-authored hub-spoke · craft-anchors.js · iframe SSoT",
        "filter": "craft",
        "items": [
            {"title": "craft-hub-spoke", "badge": "golden", "href": "diagrams/examples/craft-hub-spoke.html", "desc": "Zone labels · legend · 6 spokes · data-anchor", "tags": ["craft", "hub"]},
            {"title": "craft-deploy-flow", "badge": "golden", "href": "diagrams/examples/craft-deploy-flow.html", "desc": "Promote flow · curve h in craft-edges", "tags": ["craft", "deploy"]},
            {"title": "craft-diagram-starter", "badge": "preview", "href": "diagrams/examples/craft-diagram-starter-preview.html", "desc": "Baked demo of craft-diagram-starter scaffold", "tags": ["craft", "starter"]},
        ],
    },
    {
        "id": "fd-engine",
        "title": "fd-engine goldens",
        "subtitle": "Premium node-edge diagrams — descriptor + gen-fd.py",
        "filter": "fd-engine",
        "items": [
            {"title": "fd-architecture", "badge": "golden", "href": "graph-templates/examples/fd-architecture.html", "desc": "Canonical architecture + useCases[]", "tags": ["fd-engine", "architecture"]},
            {"title": "fd-architecture-uc", "badge": "golden", "href": "graph-templates/examples/fd-architecture-uc.html", "desc": "Particles + interactions smoke test", "tags": ["fd-engine"]},
        ],
    },
    {
        "id": "fgraph-golden",
        "title": "fgraph goldens",
        "subtitle": "Static print-safe diagrams ≤6 nodes",
        "filter": "fgraph",
        "items": [
            {"title": "system-architecture", "badge": "golden", "href": "graph-templates/examples/system-architecture.html", "desc": "Full-system fgraph reference", "tags": ["fgraph", "architecture"]},
        ],
    },
    {
        "id": "fgraph-templates",
        "title": "fgraph templates",
        "subtitle": "forge-chart authoring shells — baked demos (craft goldens: craft-hub-spoke)",
        "filter": "fgraph",
        "items": [
            {"title": "lane-swim", "badge": "preview", "href": "graph-templates/examples/lane-swim-preview.html", "desc": "Baked swimlane preview (scaffold: lane-swim.html)", "tags": ["fgraph", "swimlane"]},
            {"title": "radial-hub", "badge": "preview", "href": "graph-templates/examples/radial-hub-preview.html", "desc": "Baked hub-spoke preview", "tags": ["fgraph", "hub"]},
            {"title": "linear-flow", "badge": "preview", "href": "graph-templates/examples/linear-flow-preview.html", "desc": "Baked horizontal pipeline preview", "tags": ["fgraph", "flow"]},
            {"title": "layered", "badge": "preview", "href": "graph-templates/examples/layered-preview.html", "desc": "Baked layered tiers preview", "tags": ["fgraph", "layers"]},
            {"title": "deployment-tiers", "badge": "preview", "href": "graph-templates/examples/deployment-tiers-preview.html", "desc": "Baked environment tiers preview", "tags": ["fgraph"]},
            {"title": "machine-clusters", "badge": "preview", "href": "graph-templates/examples/machine-clusters-preview.html", "desc": "Baked multi-host clusters preview", "tags": ["fgraph"]},
            {"title": "dual-cluster", "badge": "preview", "href": "graph-templates/examples/dual-cluster-preview.html", "desc": "Baked two-cluster comparison preview", "tags": ["fgraph"]},
            {"title": "radial-ring", "badge": "preview", "href": "graph-templates/examples/radial-ring-preview.html", "desc": "Baked ring topology preview", "tags": ["fgraph"]},
            {"title": "dep-graph", "badge": "preview", "href": "graph-templates/examples/dep-graph-preview.html", "desc": "Baked dependency graph preview", "tags": ["fgraph", "deps"]},
            {"title": "funnel", "badge": "preview", "href": "graph-templates/examples/funnel-preview.html", "desc": "Baked funnel chart preview", "tags": ["fgraph"]},
            {"title": "scatter", "badge": "preview", "href": "graph-templates/examples/scatter-preview.html", "desc": "Baked scatter chart preview", "tags": ["fgraph", "chart"]},
            {"title": "bubble", "badge": "preview", "href": "graph-templates/examples/bubble-preview.html", "desc": "Baked bubble chart preview", "tags": ["fgraph", "chart"]},
            {"title": "radar", "badge": "preview", "href": "graph-templates/examples/radar-preview.html", "desc": "Baked radar chart preview", "tags": ["fgraph", "chart"]},
        ],
    },
    {
        "id": "gallery-templates",
        "title": "Gallery templates",
        "subtitle": "Image / audio gallery shells — gallery-base.css + JS",
        "filter": "gallery",
        "items": [
            {"title": "simple-gallery", "badge": "preview", "href": "gallery-templates/examples/simple-gallery-preview.html", "desc": "Baked batch filter + lightbox grid", "tags": ["gallery"]},
            {"title": "pivot-gallery", "badge": "preview", "href": "gallery-templates/examples/pivot-gallery-preview.html", "desc": "Baked pivot grouping preview", "tags": ["gallery"]},
            {"title": "comparison-gallery", "badge": "preview", "href": "gallery-templates/examples/comparison-gallery-preview.html", "desc": "Baked side-by-side comparison preview", "tags": ["gallery"]},
            {"title": "multi-mode-gallery", "badge": "preview", "href": "gallery-templates/examples/multi-mode-gallery-preview.html", "desc": "Baked multi-mode dataset preview", "tags": ["gallery"]},
            {"title": "audio-gallery", "badge": "preview", "href": "gallery-templates/examples/audio-gallery-preview.html", "desc": "Baked audio gallery preview", "tags": ["gallery", "audio"]},
        ],
    },
]


def _catalog_items_existing() -> list[dict]:
    """Return sections with only items whose href exists under references/."""
    out = []
    for section in SHOWCASE_CATALOG:
        items = []
        for item in section["items"]:
            if (REFS / item["href"]).exists():
                items.append(item)
        if items:
            out.append({**section, "items": items})
    return out


def build_showcase_index() -> None:
    sections = _catalog_items_existing()
    total = sum(len(s["items"]) for s in sections)
    filters = ["all"] + sorted({s["filter"] for s in sections})

    def thumb_slug(item: dict) -> str:
        return Path(item["href"]).stem

    def card_html(item: dict) -> str:
        tags = " ".join(item.get("tags", []))
        slug = thumb_slug(item)
        return f"""
      <article class="card" data-filter-tags="{tags}" data-title="{item['title'].lower()}">
        <a class="card-hit" href="{item['href']}" target="_blank" rel="noopener">
          <div class="card-thumb">
            <img src="thumbs/{slug}.png" alt="{item['title']} preview" loading="lazy"
                 onerror="this.remove();this.parentElement.classList.add('no-thumb')">
            <span class="card-slug">{item['title']}</span>
          </div>
          <div class="card-body">
            <h3 class="card-title">{item['title']}</h3>
            <p class="card-desc">{item['desc']}</p>
            <div class="card-meta">
              <span class="card-badge badge-{item['badge']}">{item['badge']}</span>
              <span class="card-open">open ↗</span>
            </div>
          </div>
        </a>
      </article>"""

    sections_html = []
    nav_html = []
    for section in sections:
        nav_html.append(
            f'<a href="#{section["id"]}">{section["title"]} ({len(section["items"])})</a>'
        )
        cards = "\n".join(card_html(i) for i in section["items"])
        sections_html.append(f"""
<section class="section" id="{section['id']}" data-section-filter="{section['filter']}">
  <div class="section-head">
    <div>
      <h2>{section['title']}</h2>
      <p class="section-sub">{section['subtitle']}</p>
    </div>
    <span class="count">{len(section['items'])}</span>
  </div>
  <div class="grid">{cards}
  </div>
</section>""")

    filter_btns = "".join(
        f'<button type="button" class="filter-btn{" active" if f == "all" else ""}" data-filter="{f}">{f}</button>'
        for f in filters
    )

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="diagram:title" content="Forge Reference Showcase">
  <meta name="diagram:category" content="demo">
  <title>Forge — Reference Showcase · {total} artifacts</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0d1117; --panel: #13191f; --surface: #161b22;
      --border: #21262d; --border-hi: #30363d;
      --text: #f0ede6; --text-muted: #9ca3af; --text-dim: #6b7280;
      --accent: #f0b429; --accent-dim: rgba(240,180,41,0.12);
      --cyan: #38bdf8; --green: #34d399;
    }}
    body {{
      font-family: 'IBM Plex Sans', system-ui, sans-serif;
      background: var(--bg); color: var(--text);
      line-height: 1.5; padding-bottom: 80px;
    }}
    .hero {{
      padding: 48px 40px 36px;
      border-bottom: 1px solid var(--border);
      background: radial-gradient(ellipse 80% 60% at 50% -20%, rgba(240,180,41,0.08), transparent 70%);
      position: sticky; top: 0; z-index: 50;
      backdrop-filter: blur(12px);
      background-color: color-mix(in srgb, var(--bg) 88%, transparent);
    }}
    .hero-eyebrow {{
      font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
      letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent);
    }}
    .hero h1 {{ font-size: clamp(1.5rem, 3vw, 2rem); font-weight: 700; margin: 8px 0; letter-spacing: -0.02em; }}
    .hero p {{ color: var(--text-muted); max-width: 62ch; font-size: 0.92rem; }}
    .hero-meta {{
      display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px;
      font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--text-dim);
    }}
    .hero-meta span {{ padding: 4px 10px; border: 1px solid var(--border); border-radius: 6px; }}
    .toolbar {{
      display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
      margin-top: 20px;
    }}
    .search {{
      flex: 1; min-width: 200px; max-width: 320px;
      background: var(--surface); border: 1px solid var(--border-hi);
      border-radius: 8px; padding: 8px 12px; color: var(--text);
      font-family: inherit; font-size: 0.85rem;
    }}
    .search:focus {{ outline: none; border-color: var(--accent); }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .filter-btn {{
      background: var(--surface); border: 1px solid var(--border);
      color: var(--text-muted); border-radius: 6px; padding: 6px 12px;
      font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem;
      cursor: pointer; text-transform: lowercase;
    }}
    .filter-btn:hover {{ border-color: var(--border-hi); color: var(--text); }}
    .filter-btn.active {{ border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }}
    .section-nav {{
      display: flex; flex-wrap: wrap; gap: 12px; margin-top: 14px;
    }}
    .section-nav a {{
      color: var(--cyan); text-decoration: none; font-size: 0.78rem;
    }}
    .section-nav a:hover {{ text-decoration: underline; }}
    .section {{ padding: 32px 40px; }}
    .section-head {{
      display: flex; align-items: flex-start; justify-content: space-between;
      gap: 16px; margin-bottom: 20px;
    }}
    .section-head h2 {{ font-size: 1.1rem; font-weight: 600; }}
    .section-sub {{ color: var(--text-dim); font-size: 0.82rem; margin-top: 4px; }}
    .count {{
      font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
      padding: 4px 10px; border: 1px solid var(--border); border-radius: 20px; color: var(--text-dim);
      white-space: nowrap;
    }}
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px;
    }}
    .card {{
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 10px; overflow: hidden; transition: border-color 0.15s, transform 0.15s;
    }}
    .card:hover {{ border-color: color-mix(in srgb, var(--accent) 45%, var(--border)); transform: translateY(-2px); }}
    .card.hidden {{ display: none; }}
    .card-hit {{ display: block; text-decoration: none; color: inherit; height: 100%; }}
    .card-thumb {{
      height: 100px; background: linear-gradient(135deg, #0f141a, #1a2332);
      position: relative; overflow: hidden;
      border-bottom: 1px solid var(--border);
    }}
    .card-thumb img {{
      width: 100%; height: 100%; display: block;
      object-fit: cover; object-position: top center;
    }}
    .card-thumb.no-thumb, .card-thumb:not(:has(img)) {{
      display: flex; align-items: center; justify-content: center;
    }}
    .card-slug {{
      font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem;
      color: var(--text-dim); padding: 0 12px; text-align: center;
      display: none;
    }}
    .card-thumb.no-thumb .card-slug, .card-thumb:not(:has(img)) .card-slug {{
      display: block;
    }}
    .card-body {{ padding: 14px; }}
    .card-title {{ font-size: 0.92rem; font-weight: 600; margin-bottom: 6px; }}
    .card-desc {{ font-size: 0.78rem; color: var(--text-muted); line-height: 1.45; min-height: 2.9em; }}
    .card-meta {{ display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }}
    .card-badge {{
      font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem;
      padding: 3px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em;
    }}
    .badge-skill {{ background: var(--accent-dim); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }}
    .badge-golden {{ background: rgba(56,189,248,0.12); color: var(--cyan); border: 1px solid rgba(56,189,248,0.25); }}
    .badge-template {{ background: rgba(52,211,153,0.1); color: var(--green); border: 1px solid rgba(52,211,153,0.22); }}
    .badge-starter {{ background: rgba(107,114,128,0.15); color: var(--text-dim); border: 1px solid var(--border); }}
    .badge-preview {{ background: rgba(56,189,248,0.1); color: var(--cyan); border: 1px solid rgba(56,189,248,0.22); }}
    .card-open {{ font-size: 0.72rem; color: var(--cyan); }}
    .stats-bar {{
      position: fixed; bottom: 0; left: 0; right: 0;
      padding: 10px 40px; background: color-mix(in srgb, var(--bg) 92%, transparent);
      border-top: 1px solid var(--border); backdrop-filter: blur(8px);
      font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--text-dim);
      display: flex; justify-content: space-between; z-index: 40;
    }}
    .plugin-note {{ color: var(--accent); }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-eyebrow">roxabi-forge plugin · references/</div>
    <h1>Reference Showcase</h1>
    <p>Every HTML page and diagram type the forge skills can produce — golden outputs, craft diagrams, fd-engine, fgraph templates, and gallery shells. All paths are relative to this file inside the plugin.</p>
    <div class="hero-meta">
      <span>{total} artifacts</span>
      <span>file:// safe</span>
      <span class="plugin-note">bundled in plugin</span>
    </div>
    <div class="toolbar">
      <input class="search" type="search" id="search" placeholder="Filter by name…" aria-label="Search references">
      <div class="filters" id="filters">{filter_btns}</div>
    </div>
    <nav class="section-nav" aria-label="Sections">{"".join(nav_html)}</nav>
  </header>
  <main id="main">{"".join(sections_html)}</main>
  <div class="stats-bar">
    <span id="visible-count">{total} / {total} visible</span>
    <span>plugins/forge/references/showcase-index.html</span>
  </div>
  <script>
    (function () {{
      var cards = document.querySelectorAll('.card');
      var sections = document.querySelectorAll('.section');
      var search = document.getElementById('search');
      var activeFilter = 'all';
      var countEl = document.getElementById('visible-count');

      function apply() {{
        var q = (search.value || '').trim().toLowerCase();
        var visible = 0;
        cards.forEach(function (card) {{
          var tags = card.dataset.filterTags || '';
          var title = card.dataset.title || '';
          var section = card.closest('.section');
          var sectionFilter = section ? section.dataset.sectionFilter : '';
          var matchFilter = activeFilter === 'all' || sectionFilter === activeFilter || tags.indexOf(activeFilter) >= 0;
          var matchSearch = !q || title.indexOf(q) >= 0 || tags.indexOf(q) >= 0;
          var show = matchFilter && matchSearch;
          card.classList.toggle('hidden', !show);
          if (show) visible++;
        }});
        sections.forEach(function (sec) {{
          var any = sec.querySelector('.card:not(.hidden)');
          sec.style.display = any ? '' : 'none';
        }});
        countEl.textContent = visible + ' / ' + cards.length + ' visible';
      }}

      document.getElementById('filters').addEventListener('click', function (e) {{
        var btn = e.target.closest('.filter-btn');
        if (!btn) return;
        document.querySelectorAll('.filter-btn').forEach(function (b) {{ b.classList.remove('active'); }});
        btn.classList.add('active');
        activeFilter = btn.dataset.filter;
        apply();
      }});
      search.addEventListener('input', apply);
    }})();
  </script>
</body>
</html>"""
    index_path = REFS / "showcase-index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"wrote showcase-index.html ({total} artifacts)")

    # Root redirect for legacy reference-gallery.html (deployed to ~/.roxabi/forge/)
    redirect = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=references/showcase-index.html">
  <title>Redirect — Forge Reference Showcase</title>
  <script>location.replace('references/showcase-index.html');</script>
</head>
<body>
  <p><a href="references/showcase-index.html">Forge Reference Showcase</a></p>
</body>
</html>"""
    (REFS / "reference-gallery.html").write_text(redirect, encoding="utf-8")
    print("wrote reference-gallery.html (redirect → showcase-index.html)")


def sync_craft_starter_inline_js() -> None:
    """Re-inline sanitized craft-anchors.js into the starter scaffold."""
    import importlib.util

    bake_spec = importlib.util.spec_from_file_location(
        "bake_reference_previews", ROOT / "scripts" / "bake-reference-previews.py"
    )
    if bake_spec is None or bake_spec.loader is None:
        return
    bake = importlib.util.module_from_spec(bake_spec)
    bake_spec.loader.exec_module(bake)
    path = REFS / "diagrams" / "craft-diagram-starter.html"
    if not path.exists():
        return
    text = bake.replace_craft_script_block(path.read_text(encoding="utf-8"))
    path.write_text(text, encoding="utf-8")
    print("refreshed craft-diagram-starter.html craft-anchors")


def main() -> None:
    build_craft_hub_spoke()
    build_craft_deploy_flow()
    sync_craft_starter_inline_js()
    build_showcase_presentation()
    build_showcase_epic()
    build_showcase_guide()
    build_showcase_slides()
    build_showcase_gallery()
    build_showcase_md()
    import importlib.util

    bake_spec = importlib.util.spec_from_file_location(
        "bake_reference_previews", ROOT / "scripts" / "bake-reference-previews.py"
    )
    if bake_spec and bake_spec.loader:
        bake_mod = importlib.util.module_from_spec(bake_spec)
        bake_spec.loader.exec_module(bake_mod)
        bake_mod.main()
    build_showcase_index()
    print("done — run validate-reference-runtime.py to validate")


if __name__ == "__main__":
    main()