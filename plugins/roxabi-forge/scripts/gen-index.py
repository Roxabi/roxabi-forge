#!/usr/bin/env python3
"""gen-index.py — génère site/index.html (shell) + manifest.json (worker-only).

Landing façon roxabi-forge. DATA cards come from GET /api/catalogue
(anonymous = public only; Access JWT = all). manifest.json is blocked
from clients; the Function reads it via ASSETS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent / "lib"
if _LIB.is_dir() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))


def _resolve_paths() -> tuple[Path, Path, Path, Path, Path]:
    """repo ROOT, registry, site, index out, manifest — config-aware with defaults."""
    root = Path(__file__).resolve().parents[3]
    site_dir = "site"
    reg_dir = "registry"
    try:
        from load_config import load_config

        cfg = load_config()
        site_dir = str(cfg.get("site_dir") or site_dir)
        reg_dir = str(cfg.get("registry_dir") or reg_dir)
    except Exception:
        pass
    site = root / site_dir
    return root, root / reg_dir, site, site / "index.html", site / "manifest.json"


ROOT, REG, SITE, OUT, MANIFEST = _resolve_paths()

TYPE_LABEL = {
    "talk": "Talk",
    "deck": "Deck",
    "guide": "Guide",
    "diagram": "Diagramme",
    "gallery": "Galerie",
    "html": "HTML",
    "other": "Artefact",
}

# Color token keys used by CSS (match roxabi group-tag / card classes)
TYPE_COLOR = {
    "talk": "purple",
    "deck": "blue",
    "guide": "green",
    "diagram": "amber",
    "gallery": "cyan",
    "html": "orange",
    "other": "gold",
}


def load_items() -> list[dict]:
    items: list[dict] = []
    if not REG.is_dir():
        return items
    for p in sorted(REG.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {p.name}: {e}", file=sys.stderr)
            continue
        if not data.get("slug") or not data.get("title"):
            print(f"skip {p.name}: slug/title required", file=sys.stderr)
            continue
        if data.get("list_on_index", True) is False:
            continue
        data.setdefault("type", "html")
        data.setdefault("description", "")
        data.setdefault("date", "")
        data["path"] = data.get("path") or f"/a/{data['slug']}/"
        # Snapshot only — never persist share keys in registry; live badge = GET /api/share
        data["shared"] = bool(data.get("shared"))
        # /p/ purged — only /a/ (Access) + /s/ (share key)
        items.append(data)
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    return items


def file_kb(item: dict) -> int:
    """Size of the main HTML for display (kb), 0 if missing."""
    rel = str(item["path"]).lstrip("/")
    candidates = [
        SITE / rel / "index.html",
        SITE / rel.rstrip("/") ,
    ]
    if rel.endswith(".html"):
        candidates.insert(0, SITE / rel)
    for c in candidates:
        if c.is_file():
            return max(1, c.stat().st_size // 1024)
    return 0


def preview_info(item: dict) -> tuple[bool, str]:
    """Return (has_preview, thumb_url) if an og/thumb image exists on disk."""
    slug = item["slug"]
    rel = str(item["path"]).lstrip("/").rstrip("/")
    # Prefer compressed JPEG from gen-og-images.sh; fall back to legacy PNG
    candidates = [
        (SITE / rel / "og.jpg", f"/{rel}/og.jpg"),
        (SITE / rel / "og.jpeg", f"/{rel}/og.jpeg"),
        (SITE / rel / "og.png", f"/{rel}/og.png"),
        (SITE / rel / "index.og.png", f"/{rel}/index.og.png"),
        (SITE / rel / f"{slug}.og.png", f"/{rel}/{slug}.og.png"),
        (SITE / "images" / f"{slug}.og.jpg", f"/images/{slug}.og.jpg"),
        (SITE / "images" / f"{slug}.og.png", f"/images/{slug}.og.png"),
        (SITE / "images" / f"{slug}.png", f"/images/{slug}.png"),
    ]
    for path, url in candidates:
        if path.is_file():
            return True, url
    return False, ""


def to_manifest(items: list[dict]) -> list[dict]:
    """Compact client payload: the catalogue fields plus slug / share / description."""
    out = []
    for it in items:
        t = it.get("type") or "html"
        has_p, thumb = preview_info(it)
        badges: list[str] = []
        is_shared = bool(it.get("shared"))
        if is_shared:
            badges.append("share")
        out.append(
            {
                "f": it["path"],
                "t": it["title"],
                "d": it.get("date") or "",
                "cat": t,
                "cl": TYPE_LABEL.get(t, t.title()),
                "c": TYPE_COLOR.get(t, "gold"),
                "b": badges,
                "kb": file_kb(it),
                "p": has_p,
                "thumb": thumb,
                "desc": it.get("description") or "",
                "slug": it["slug"],
                "shared": is_shared,
            }
        )
    return out


def render(manifest: list[dict]) -> str:
    _ = manifest  # written separately to manifest.json for the worker
    return f"""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Roxabi Forge</title>
<meta name="description" content="Diagrammes interactifs, galeries et artefacts visuels de l’écosystème Roxabi. Pages publiques ici ; le reste derrière Cloudflare Access.">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#0c0e16">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://forge.roxabi.dev/">
<meta property="og:title" content="Roxabi Forge">
<meta property="og:description" content="Diagrammes, galeries et artefacts HTML autoportants.">
<meta property="og:site_name" content="Roxabi Forge">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0c0e16; --surface:#13161f; --surface2:#1a1d2a; --card:#1e2133;
  --border:rgba(255,255,255,0.07); --border2:rgba(255,255,255,0.13);
  --text:#dde4f0; --text-dim:#7d8799; --text-xdim:#3e4556;
  --accent:#e8a030; --accent-dim:rgba(232,160,48,0.12);
  --green:#34d399;  --green-dim:rgba(52,211,153,0.12);
  --blue:#60a5fa;   --blue-dim:rgba(96,165,250,0.12);
  --purple:#a78bfa; --purple-dim:rgba(167,139,250,0.12);
  --orange:#fb923c; --orange-dim:rgba(251,146,60,0.12);
  --cyan:#22d3ee;   --cyan-dim:rgba(34,211,238,0.12);
  --red:#f87171;    --red-dim:rgba(248,113,113,0.12);
  --gold:#fbbf24;   --gold-dim:rgba(251,191,36,0.12);
  --font:'Plus Jakarta Sans',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,monospace;
}}
[data-theme="light"] {{
  --bg:#f5f2ec; --surface:#ede9e0; --surface2:#e5e0d5; --card:#faf8f4;
  --border:rgba(0,0,0,0.08); --border2:rgba(0,0,0,0.15);
  --text:#1a1d2b; --text-dim:#5a6070; --text-xdim:#9aa0ae;
  --accent:#b8760a; --accent-dim:rgba(184,118,10,0.1);
  --green:#047857; --green-dim:rgba(4,120,87,0.1);
  --blue:#1d4ed8;  --blue-dim:rgba(29,78,216,0.1);
  --purple:#7c3aed;--purple-dim:rgba(124,58,237,0.1);
  --orange:#ea580c; --orange-dim:rgba(234,88,12,0.1);
  --cyan:#0891b2;   --cyan-dim:rgba(8,145,178,0.1);
  --red:#dc2626;    --red-dim:rgba(220,38,38,0.1);
  --gold:#d97706;   --gold-dim:rgba(217,119,6,0.1);
}}

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{font-size:15px;-webkit-font-smoothing:antialiased}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;transition:background .2s,color .2s}}
.layout{{max-width:1200px;margin:0 auto;padding:28px 24px 64px}}

/* ── Header ── */
.header{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:24px 0 20px;border-bottom:1px solid var(--border);margin-bottom:14px}}
.header-brand{{display:flex;flex-direction:column;gap:6px}}
.header-kicker{{
  display:inline-flex;align-items:center;gap:8px;align-self:flex-start;
  font-size:.62rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  color:var(--blue);background:var(--blue-dim);border:1px solid color-mix(in srgb,var(--blue) 35%,transparent);
  border-radius:999px;padding:4px 10px;
}}
.header-kicker-dot{{width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--accent-dim)}}
.header-title{{font-size:1.4rem;font-weight:700;letter-spacing:-0.02em}}
.header-title span{{color:var(--accent)}}
.header-sub{{font-size:.8rem;color:var(--text-dim);margin-top:4px;max-width:36rem;line-height:1.45}}
.header-actions{{display:flex;align-items:center;gap:8px;flex-shrink:0}}
.theme-btn{{background:var(--surface);border:1px solid var(--border2);border-radius:6px;color:var(--text-dim);cursor:pointer;font-size:.85rem;padding:5px 10px;transition:border-color .15s,color .15s;line-height:1}}
.theme-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.ghost-btn{{
  background:transparent;border:1px solid color-mix(in srgb,var(--text) 16%,transparent);
  color:var(--text-xdim);cursor:pointer;font-size:.68rem;font-weight:500;letter-spacing:.06em;
  padding:4px 9px;border-radius:6px;text-decoration:none;opacity:.65;
  transition:opacity .15s,border-color .15s,color .15s;line-height:1.2;
}}
.ghost-btn:hover{{opacity:1;color:var(--text-dim);border-color:color-mix(in srgb,var(--text) 32%,transparent)}}

/* ── Stats strip ── */
.stats{{display:flex;flex-wrap:wrap;gap:10px 18px;margin-bottom:8px;font-family:var(--mono);font-size:.72rem;color:var(--text-xdim)}}
.stats b{{color:var(--text);font-weight:500}}
.share-sync{{font-size:.62rem;opacity:.75}}
.share-sync.ok{{color:var(--green)}}
.share-sync.err{{color:var(--orange)}}
.share-sync.loading{{color:var(--text-xdim)}}

/* ── Toolbar ── */
.toolbar{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 0 16px;border-bottom:1px solid var(--border);margin-bottom:24px}}
.toolbar-left{{display:flex;align-items:center;gap:8px;flex:1;min-width:180px}}
.toolbar-right{{display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
.ctrl-group{{display:flex;align-items:center;gap:5px}}
.ctrl-label{{font-size:.62rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--text-xdim);font-family:var(--mono);white-space:nowrap}}
.segs{{display:flex;background:var(--surface);border:1px solid var(--border);border-radius:6px;overflow:hidden}}
.seg{{background:none;border:none;border-right:1px solid var(--border);color:var(--text-dim);cursor:pointer;font-family:var(--font);font-size:.72rem;font-weight:500;padding:5px 11px;transition:background .12s,color .12s;white-space:nowrap}}
.seg:last-child{{border-right:none}}
.seg:hover{{background:var(--surface2);color:var(--text)}}
.seg.on{{background:var(--accent-dim);color:var(--accent);font-weight:600}}

/* ── Search ── */
.search-wrap{{position:relative;flex:1;max-width:280px}}
.search-wrap::before{{content:'⌕';position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--text-xdim);font-size:.9rem;pointer-events:none}}
.search-wrap input{{background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:.75rem;padding:6px 10px 6px 28px;width:100%;outline:none;transition:border-color .15s}}
.search-wrap input:focus{{border-color:var(--accent)}}
.search-wrap input::placeholder{{color:var(--text-xdim)}}
.count{{font-family:var(--mono);font-size:.65rem;color:var(--text-xdim);white-space:nowrap}}

/* ── Group section ── */
.group-sec{{margin-bottom:32px}}
.group-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
.group-tag{{font-size:.61rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;padding:2px 8px;border-radius:4px;font-family:var(--mono)}}
.group-tag.amber{{background:var(--accent-dim);color:var(--accent);border:1px solid var(--accent)}}
.group-tag.blue{{background:var(--blue-dim);color:var(--blue);border:1px solid var(--blue)}}
.group-tag.green{{background:var(--green-dim);color:var(--green);border:1px solid var(--green)}}
.group-tag.purple{{background:var(--purple-dim);color:var(--purple);border:1px solid var(--purple)}}
.group-tag.orange{{background:var(--orange-dim);color:var(--orange);border:1px solid var(--orange)}}
.group-tag.cyan{{background:var(--cyan-dim);color:var(--cyan);border:1px solid var(--cyan)}}
.group-tag.red{{background:var(--red-dim);color:var(--red);border:1px solid var(--red)}}
.group-tag.gold{{background:var(--gold-dim);color:var(--gold);border:1px solid var(--gold)}}
.group-tag.neutral{{background:var(--surface2);color:var(--text-dim);border:1px solid var(--border2)}}
.group-cnt{{font-family:var(--mono);font-size:.64rem;color:var(--text-xdim)}}

/* ── Card grid ── */
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:0;overflow:hidden;text-decoration:none;display:flex;flex-direction:column;transition:border-color .15s,transform .12s,box-shadow .15s;color:inherit;position:relative}}
.card:hover{{transform:translateY(-2px)}}
/* Full-bleed thumb: edge-to-edge card width, OG aspect ratio (1200×630) */
.card-thumb{{width:100%;aspect-ratio:1200/630;overflow:hidden;background:var(--surface2);border-bottom:1px solid var(--border);position:relative;flex-shrink:0;margin:0;padding:0;line-height:0}}
.card-thumb img{{width:100%;height:100%;object-fit:cover;object-position:top center;display:block;transition:transform .25s ease}}
.card:hover .card-thumb img{{transform:scale(1.025)}}
.card-thumb.no-preview{{display:flex;align-items:center;justify-content:center;line-height:normal;min-height:120px;aspect-ratio:1200/630}}
.card-thumb.no-preview::before{{content:'⊞';font-size:1.75rem;color:var(--text-xdim);opacity:.32;line-height:1}}
.card.amber .card-thumb.no-preview{{background:var(--accent-dim)}}
.card.blue .card-thumb.no-preview{{background:var(--blue-dim)}}
.card.green .card-thumb.no-preview{{background:var(--green-dim)}}
.card.purple .card-thumb.no-preview{{background:var(--purple-dim)}}
.card.orange .card-thumb.no-preview{{background:var(--orange-dim)}}
.card.cyan .card-thumb.no-preview{{background:var(--cyan-dim)}}
.card.red .card-thumb.no-preview{{background:var(--red-dim)}}
.card.gold .card-thumb.no-preview{{background:var(--gold-dim)}}
.card-body{{padding:12px 14px 14px;display:flex;flex-direction:column;gap:6px;flex:1}}
.card.amber:hover{{border-color:var(--accent);box-shadow:0 5px 18px rgba(232,160,48,.12)}}
.card.blue:hover{{border-color:var(--blue);box-shadow:0 5px 18px rgba(96,165,250,.12)}}
.card.green:hover{{border-color:var(--green);box-shadow:0 5px 18px rgba(52,211,153,.12)}}
.card.purple:hover{{border-color:var(--purple);box-shadow:0 5px 18px rgba(167,139,250,.12)}}
.card.orange:hover{{border-color:var(--orange);box-shadow:0 5px 18px rgba(251,146,60,.12)}}
.card.cyan:hover{{border-color:var(--cyan);box-shadow:0 5px 18px rgba(34,211,238,.12)}}
.card.red:hover{{border-color:var(--red);box-shadow:0 5px 18px rgba(248,113,113,.12)}}
.card.gold:hover{{border-color:var(--gold);box-shadow:0 5px 18px rgba(251,191,36,.12)}}
.card-title{{font-size:.83rem;font-weight:600;color:var(--text);line-height:1.4}}
.card-desc{{font-size:.78rem;line-height:1.45;color:var(--text-dim);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.card-meta{{display:flex;align-items:center;gap:4px;flex-wrap:wrap}}
.card-meta span{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim)}}
.card-file{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}

/* ── List view ── */
.list-view{{display:flex;flex-direction:column;gap:1px}}
.list-item{{display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:7px;text-decoration:none;color:inherit;transition:background .12s}}
.list-item:hover{{background:var(--surface)}}
.li-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.li-dot.amber{{background:var(--accent)}}
.li-dot.blue{{background:var(--blue)}}
.li-dot.green{{background:var(--green)}}
.li-dot.purple{{background:var(--purple)}}
.li-dot.orange{{background:var(--orange)}}
.li-dot.cyan{{background:var(--cyan)}}
.li-dot.red{{background:var(--red)}}
.li-dot.gold{{background:var(--gold)}}
.li-title{{font-size:.82rem;font-weight:500;color:var(--text);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.li-cat{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim);flex-shrink:0;min-width:80px}}
.li-file{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim);flex-shrink:0}}
.li-date{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim);flex-shrink:0}}
.li-size{{font-family:var(--mono);font-size:.62rem;color:var(--text-xdim);flex-shrink:0;min-width:44px;text-align:right}}
@media(max-width:860px){{.li-file{{display:none}}}}
@media(max-width:700px){{.li-cat{{display:none}}}}

/* ── Badges ── */
.badges{{display:flex;gap:3px;flex-shrink:0;flex-wrap:wrap}}
.badge{{font-family:var(--mono);font-size:.56rem;font-weight:600;padding:1px 5px;border-radius:3px;text-transform:uppercase;letter-spacing:.05em}}
.badge.share{{background:var(--accent-dim);color:var(--accent);border:1px solid var(--accent)}}
.badge.internal{{background:var(--blue-dim);color:var(--blue);border:1px solid var(--blue)}}
.badge.latest{{background:var(--green-dim);color:var(--green);border:1px solid var(--green)}}
.badge.draft{{background:var(--orange-dim);color:var(--orange);border:1px solid var(--orange)}}

/* ── Star ── */
.star-btn{{background:none;border:none;cursor:pointer;font-size:.92rem;line-height:1;padding:2px;color:var(--text-xdim);transition:color .12s,transform .12s;flex-shrink:0}}
.star-btn:hover{{color:var(--gold);transform:scale(1.2)}}
.star-btn.on{{color:var(--gold)}}
.card .star-btn{{position:absolute;top:8px;right:8px;z-index:2;background:rgba(12,14,22,.58);border-radius:5px;backdrop-filter:blur(4px);color:#dde4f0}}
[data-theme="light"] .card .star-btn{{background:rgba(250,248,244,.78);color:var(--text-xdim)}}
[data-theme="light"] .card .star-btn.on{{color:var(--gold)}}

.empty{{padding:48px 0;text-align:center;font-size:.84rem;color:var(--text-xdim)}}
.empty code{{font-family:var(--mono);font-size:.78rem;background:var(--surface);padding:1px 6px;border-radius:3px}}
.note{{margin-top:28px;font-size:.78rem;line-height:1.55;color:var(--text-xdim);max-width:40rem}}
.note code{{font-family:var(--mono);font-size:.72rem;background:var(--surface);padding:1px 5px;border-radius:3px}}
.note a{{color:var(--blue);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--blue) 35%,transparent)}}
footer{{margin-top:40px;padding-top:16px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:10px 18px;justify-content:space-between;font-size:.75rem;color:var(--text-xdim)}}
footer a{{color:var(--text-xdim);text-decoration:none}}
footer a:hover{{color:var(--blue)}}
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:3px}}
/* Selection (team only): the checkbox sits inside the card anchor, so it has to
   stop the click from navigating — same pattern as the star button. */
.sel-box{{position:absolute;top:8px;left:8px;z-index:2;width:18px;height:18px;border-radius:5px;
  border:1px solid var(--border2);background:rgba(12,14,22,.58);backdrop-filter:blur(4px);
  cursor:pointer;display:none;align-items:center;justify-content:center;padding:0;
  color:#dde4f0;font-size:.7rem;line-height:1;flex-shrink:0}}
[data-theme="light"] .sel-box{{background:rgba(250,248,244,.78);color:var(--text-xdim)}}
.list-item .sel-box{{position:static;width:16px;height:16px;background:none;backdrop-filter:none}}
body.team .sel-box{{display:inline-flex}}
.sel-box.on{{background:var(--accent);border-color:var(--accent);color:#0c0e16}}
.card.selected,.list-item.selected{{outline:2px solid var(--accent);outline-offset:-2px}}
.batch-bar{{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(14px);z-index:2147483646;
  display:none;gap:10px;align-items:center;background:var(--card);border:1px solid var(--border2);
  border-radius:10px;padding:8px 12px;box-shadow:0 12px 34px rgba(0,0,0,.34);
  opacity:0;transition:opacity .16s ease,transform .16s ease;max-width:min(94vw,640px);flex-wrap:wrap}}
.batch-bar.on{{display:flex;opacity:1;transform:translateX(-50%) translateY(0)}}
.batch-count{{font-size:.72rem;color:var(--text-dim);font-family:var(--mono)}}
.batch-bar button{{cursor:pointer;border:1px solid var(--border2);background:var(--surface);color:var(--text-dim);
  border-radius:6px;padding:5px 10px;font-size:.72rem;font-weight:600;font-family:inherit;
  transition:background .12s,color .12s,border-color .12s}}
.batch-bar button:hover:not(:disabled){{background:var(--surface2);color:var(--text)}}
.batch-bar button:disabled{{opacity:.5;cursor:wait}}
.batch-bar button.vis-public{{border-color:var(--green);color:var(--green)}}
.batch-bar button.vis-shared{{border-color:var(--accent);color:var(--accent)}}
.batch-bar button.vis-private{{border-color:var(--border2)}}
.batch-msg{{font-size:.68rem;color:var(--text-dim);font-family:var(--mono)}}
.batch-msg.err{{color:var(--red)}}
@media(max-width:580px){{.ctrl-label{{display:none}}.seg{{padding:5px 8px;font-size:.7rem}}}}
</style>
</head>
<body>
<div class="layout">

<header class="header">
  <div class="header-brand">
    <span class="header-kicker" id="headerKicker"><span class="header-kicker-dot" aria-hidden="true"></span>Catalogue public</span>
    <div class="header-title">✦ <span>Forge</span></div>
    <div class="header-sub" id="headerSub">Pages publiques. Connexion équipe pour le reste.</div>
  </div>
  <div class="header-actions">
    <a class="ghost-btn" id="loginLink" href="/login" title="Connexion équipe">Équipe</a>
    <button class="theme-btn" id="themeBtn" title="Basculer le thème" aria-label="Basculer le thème">🌙</button>
  </div>
</header>

<div class="stats">
  <span><b id="statTotal">0</b> au catalogue</span>
  <span><b id="statPublic">0</b> publiques</span>
  <span><b id="statShared">0</b> partagées</span>
  <span id="shareSync" class="share-sync" title="État share synchronisé depuis KV (live)"></span>
</div>

<div class="toolbar">
  <div class="toolbar-left">
    <div class="search-wrap">
      <input type="search" id="search" placeholder="Filtrer…" autocomplete="off" aria-label="Filtrer le catalogue">
    </div>
    <span class="count" id="count"></span>
  </div>
  <div class="toolbar-right">
    <div class="ctrl-group">
      <span class="ctrl-label">Accès</span>
      <div class="segs">
        <button type="button" class="seg" data-k="access" data-v="all">Tous</button>
        <button type="button" class="seg" data-k="access" data-v="public">Publiques</button>
        <button type="button" class="seg" data-k="access" data-v="shared">Partagées</button>
        <button type="button" class="seg" data-k="access" data-v="private">Privées</button>
      </div>
    </div>
    <div class="ctrl-group">
      <span class="ctrl-label">Grouper</span>
      <div class="segs">
        <button type="button" class="seg" data-k="group" data-v="starred">★ Favoris</button>
        <button type="button" class="seg" data-k="group" data-v="cat">Type</button>
        <button type="button" class="seg" data-k="group" data-v="date">Date</button>
        <button type="button" class="seg" data-k="group" data-v="none">Aucun</button>
      </div>
    </div>
    <div class="ctrl-group">
      <span class="ctrl-label">Trier</span>
      <div class="segs">
        <button type="button" class="seg" data-k="sort" data-v="date-desc">Récent</button>
        <button type="button" class="seg" data-k="sort" data-v="date-asc">Ancien</button>
        <button type="button" class="seg" data-k="sort" data-v="title">A → Z</button>
      </div>
    </div>
    <div class="ctrl-group">
      <span class="ctrl-label">Vue</span>
      <div class="segs">
        <button type="button" class="seg" data-k="view" data-v="card">⊞ Cartes</button>
        <button type="button" class="seg" data-k="view" data-v="list">≡ Liste</button>
      </div>
    </div>
  </div>
</div>

<div id="content"></div>

<p class="note">
  Publier : <code>plugins/roxabi-forge/scripts/publish.sh</code>.
  Doc Access : <code>docs/cloudflare-access.md</code>.
  Les pages privées restent derrière Cloudflare Access ; un lien <code>/s/…</code> ouvre une page partagée.
</p>

<footer>
  <span>© Roxabi · forge.roxabi.dev</span>
  <a href="https://roxabi.dev">roxabi.dev</a>
</footer>
</div>

<script>
// ── Data from GET /api/catalogue (never embed private titles) ────
let DATA = [];
let TEAM = false;

// ── State ─────────────────────────────────────────────────────────
const LS = {{
  theme:  'roxabi-forge-theme',
  group:  'roxabi-forge-group',
  sort:   'roxabi-forge-sort',
  view:   'roxabi-forge-view',
  access: 'roxabi-forge-access',
  stars:  'roxabi-forge-stars',
}};
const S = {{
  theme:  localStorage.getItem(LS.theme)  || 'dark',
  group:  localStorage.getItem(LS.group)  || 'cat',
  sort:   localStorage.getItem(LS.sort)   || 'date-desc',
  view:   localStorage.getItem(LS.view)   || 'card',
  access: localStorage.getItem(LS.access) || 'all',
  q: '',
}};
const stars = new Set(JSON.parse(localStorage.getItem(LS.stars) || '[]'));
function saveStar() {{ localStorage.setItem(LS.stars, JSON.stringify([...stars])); }}
function toggleStar(file, e) {{
  e.preventDefault(); e.stopPropagation();
  stars.has(file) ? stars.delete(file) : stars.add(file);
  saveStar(); render();
}}

// ── Selection & batch visibility (team only) ──────────────────────
// Selection is keyed on the page path and lives outside the DOM: cards are
// rendered batch by batch as you scroll, so anything tied to elements would
// lose what has not been drawn yet. VIEW holds the current filtered+sorted
// list, which is what "select all" and shift-range act on.
const SEL = new Set();
let VIEW = [];
let lastPick = -1;

function toggleSelect(file, e) {{
  e.preventDefault(); e.stopPropagation();
  const idx = VIEW.findIndex(d => d.f === file);
  if (e.shiftKey && lastPick >= 0 && idx >= 0) {{
    const [a, b] = lastPick < idx ? [lastPick, idx] : [idx, lastPick];
    const turnOn = !SEL.has(file);
    for (let i = a; i <= b; i++) {{
      if (turnOn) SEL.add(VIEW[i].f); else SEL.delete(VIEW[i].f);
    }}
  }} else {{
    SEL.has(file) ? SEL.delete(file) : SEL.add(file);
  }}
  if (idx >= 0) lastPick = idx;
  syncSelection();
}}

/* Repaint selection without re-rendering: render() would rebuild every section
   and drop the scroll position mid-selection. */
function syncSelection() {{
  document.querySelectorAll('[data-file]').forEach(el => {{
    const on = SEL.has(el.getAttribute('data-file'));
    el.classList.toggle('selected', on);
    const box = el.querySelector('.sel-box');
    if (box) {{
      box.classList.toggle('on', on);
      box.textContent = on ? '✓' : '';
      box.setAttribute('aria-pressed', on ? 'true' : 'false');
    }}
  }});
  const bar = document.getElementById('batchBar');
  if (!bar) return;
  bar.classList.toggle('on', TEAM && SEL.size > 0);
  const cnt = document.getElementById('batchCount');
  if (cnt) cnt.textContent = SEL.size + ' sélectionné' + (SEL.size > 1 ? 's' : '');
}}

function selBox(file) {{
  const on = SEL.has(file);
  return `<button type="button" class="sel-box${{on ? ' on' : ''}}" aria-pressed="${{on}}" title="Sélectionner (maj+clic : plage)" aria-label="Sélectionner">${{on ? '✓' : ''}}</button>`;
}}

function setBatchMsg(msg, cls) {{
  const el = document.getElementById('batchMsg');
  if (!el) return;
  el.textContent = msg || '';
  el.className = 'batch-msg' + (cls ? ' ' + cls : '');
}}

/* The API caps a call at 100 ids; chunks stay well under it so one Worker
   invocation never approaches its subrequest budget. */
const BATCH_CHUNK = 25;

async function applyBatch(visibility) {{
  const slugs = [...SEL].map(f => f.replace(/^\\//, ''));
  if (!slugs.length) return;
  const buttons = document.querySelectorAll('.batch-bar button');
  buttons.forEach(b => {{ b.disabled = true; }});
  setBatchMsg('application…', '');
  const ok = [];
  const failed = [];
  try {{
    for (let i = 0; i < slugs.length; i += BATCH_CHUNK) {{
      const chunk = slugs.slice(i, i + BATCH_CHUNK);
      const r = await fetch('/api/visibility', {{
        method: 'POST',
        credentials: 'same-origin',
        headers: {{ 'content-type': 'application/json', accept: 'application/json' }},
        body: JSON.stringify({{ slugs: chunk, visibility }}),
      }});
      if (!r.ok) {{
        chunk.forEach(s => failed.push({{ slug: s, error: 'http_' + r.status }}));
        continue;
      }}
      const data = await r.json();
      (data.ok || []).forEach(s => ok.push(s));
      (data.failed || []).forEach(f => failed.push(f));
      setBatchMsg(`${{ok.length + failed.length}}/${{slugs.length}}…`, '');
    }}
  }} catch (e) {{
    setBatchMsg('réseau indisponible', 'err');
    buttons.forEach(b => {{ b.disabled = false; }});
    return;
  }}
  // Applied pages leave the selection; failures stay selected so the next
  // click retries exactly what did not land.
  const applied = new Set(ok);
  DATA.forEach(d => {{
    if (applied.has(d.f.replace(/^\\//, ''))) {{
      d.visibility = visibility;
      setShared(d, visibility === 'shared');
      SEL.delete(d.f);
    }}
  }});
  buttons.forEach(b => {{ b.disabled = false; }});
  setBatchMsg(failed.length ? `${{ok.length}} appliquée(s), ${{failed.length}} en échec` : `${{ok.length}} appliquée(s)`, failed.length ? 'err' : '');
  updateShareStats();
  render();
  syncSelection();
}}

function mountBatchBar() {{
  if (document.getElementById('batchBar')) return;
  const bar = document.createElement('div');
  bar.className = 'batch-bar';
  bar.id = 'batchBar';
  bar.innerHTML = `
    <span class="batch-count" id="batchCount">0 sélectionné</span>
    <button type="button" class="vis-private" data-vis="private">Privé</button>
    <button type="button" class="vis-shared" data-vis="shared">Partagé</button>
    <button type="button" class="vis-public" data-vis="public">Public</button>
    <button type="button" data-act="all">Tout le filtre</button>
    <button type="button" data-act="clear">Effacer</button>
    <span class="batch-msg" id="batchMsg"></span>`;
  bar.querySelectorAll('[data-vis]').forEach(b => {{
    b.addEventListener('click', () => applyBatch(b.getAttribute('data-vis')));
  }});
  bar.querySelector('[data-act="all"]').addEventListener('click', () => {{
    VIEW.forEach(d => SEL.add(d.f));
    syncSelection();
  }});
  bar.querySelector('[data-act="clear"]').addEventListener('click', () => {{
    SEL.clear(); lastPick = -1; setBatchMsg('');
    syncSelection();
  }});
  document.body.appendChild(bar);
}}

const html_el    = document.documentElement;
const contentEl  = document.getElementById('content');
const countEl    = document.getElementById('count');

function escHtml(s) {{
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}}

function fmtDate(iso) {{
  if (!iso) return '—';
  const parts = iso.split('-');
  if (parts.length < 3) return iso;
  const [y,m,day] = parts;
  const months = 'janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.'.split(' ');
  return `${{months[+m-1]}} ${{+day}}, ${{y}}`;
}}

function badges(list) {{
  return (list || []).map(b => `<span class="badge ${{escHtml(b)}}">${{escHtml(b)}}</span>`).join('');
}}

function setShared(d, active) {{
  d.shared = !!active;
  const rest = (d.b || []).filter(x => x !== 'share');
  if (d.shared) rest.push('share');
  d.b = rest;
}}

function accessBadges(d) {{
  const vis = d.visibility || (d.shared ? 'shared' : 'private');
  if (vis === 'public') return badges(['public']);
  if (vis === 'shared') return badges(['share']);
  return badges(['private']);
}}

function thumbSrc(d) {{
  if (d.thumb) return d.thumb;
  const f = d.f || '';
  if (f.endsWith('.html')) return f.slice(0, -5) + '.og.jpg';
  return f.replace(/\\/?$/, '/') + 'og.jpg';
}}

function groupByKey(items, fn) {{
  const grouped = new Map();
  items.forEach(d => {{
    const k = fn(d);
    if (!grouped.has(k)) grouped.set(k, []);
    grouped.get(k).push(d);
  }});
  return grouped;
}}

function mkCard(d, showCat) {{
  const a = document.createElement('a');
  a.className = `card ${{d.c}}${{SEL.has(d.f) ? ' selected' : ''}}`;
  a.href = d.f;
  a.setAttribute('data-file', d.f);
  const starred = stars.has(d.f);
  const catSpan = showCat
    ? `<span style="color:var(--${{d.c==='amber'?'accent':d.c}})">${{escHtml(d.cl)}}</span><span>·</span>`
    : '';
  const thumbBlock = d.p
    ? `<div class="card-thumb"><img src="${{escHtml(thumbSrc(d))}}" alt="${{escHtml(d.t)}} aperçu" loading="lazy" decoding="async"></div>`
    : `<div class="card-thumb no-preview" aria-hidden="true"></div>`;
  const desc = d.desc ? `<div class="card-desc">${{escHtml(d.desc)}}</div>` : '';
  const size = d.kb ? `<span>·</span><span>${{d.kb}} kb</span>` : '';
  a.innerHTML = `
    ${{selBox(d.f)}}
    <button type="button" class="star-btn${{starred?' on':''}}" title="${{starred?'Retirer des favoris':'Ajouter aux favoris'}}" aria-label="${{starred?'Retirer des favoris':'Ajouter aux favoris'}}">${{starred?'★':'☆'}}</button>
    ${{thumbBlock}}
    <div class="card-body">
      <div class="badges">${{accessBadges(d)}}</div>
      <div class="card-title">${{escHtml(d.t)}}</div>
      ${{desc}}
      <div class="card-meta">${{catSpan}}<span>${{fmtDate(d.d)}}</span>${{size}}</div>
      <div class="card-file">${{escHtml(d.f)}}</div>
    </div>`;
  a.querySelector('.star-btn').addEventListener('click', e => toggleStar(d.f, e));
  a.querySelector('.sel-box').addEventListener('click', e => toggleSelect(d.f, e));
  if (d.p) {{
    const img = a.querySelector('.card-thumb img');
    if (img) img.addEventListener('error', () => {{
      const wrap = img.closest('.card-thumb');
      wrap.classList.add('no-preview');
      img.remove();
    }});
  }}
  return a;
}}

function mkRow(d, showCat) {{
  const a = document.createElement('a');
  a.className = 'list-item' + (SEL.has(d.f) ? ' selected' : '');
  a.href = d.f;
  a.setAttribute('data-file', d.f);
  const starred = stars.has(d.f);
  a.innerHTML = `
    ${{selBox(d.f)}}
    <button type="button" class="star-btn${{starred?' on':''}}" title="${{starred?'Retirer des favoris':'Ajouter aux favoris'}}" aria-label="${{starred?'Retirer des favoris':'Ajouter aux favoris'}}">${{starred?'★':'☆'}}</button>
    <span class="li-dot ${{escHtml(d.c)}}"></span>
    <span class="li-title">${{escHtml(d.t)}}</span>
    <span class="badges">${{accessBadges(d)}}</span>
    ${{showCat ? `<span class="li-cat">${{escHtml(d.cl)}}</span>` : ''}}
    <span class="li-file">${{escHtml(d.f)}}</span>
    <span class="li-date">${{fmtDate(d.d)}}</span>
    <span class="li-size">${{d.kb ? d.kb + ' kb' : '—'}}</span>`;
  a.querySelector('.star-btn').addEventListener('click', e => toggleStar(d.f, e));
  a.querySelector('.sel-box').addEventListener('click', e => toggleSelect(d.f, e));
  return a;
}}

// A section is emitted empty, then fed batch by batch: with 800+ artefacts,
// building every card up front costs seconds of layout and pulls every preview
// image at once. The DOM only ever holds what has been scrolled to.
function mkSection(label, color, count, showCat) {{
  const sec = document.createElement('div');
  sec.className = 'group-sec';
  if (label) {{
    sec.innerHTML = `
      <div class="group-hdr">
        <span class="group-tag ${{color}}">${{escHtml(label)}}</span>
        <span class="group-cnt">${{count}} artefact${{count!==1?'s':''}}</span>
      </div>`;
  }}
  const holder = document.createElement('div');
  holder.className = S.view === 'card' ? 'card-grid' : 'list-view';
  sec.appendChild(holder);
  sec._holder = holder;
  return sec;
}}

function fillSection(sec, items, showCat) {{
  const holder = sec._holder;
  const make = S.view === 'card' ? mkCard : mkRow;
  const frag = document.createDocumentFragment();
  items.forEach(d => frag.appendChild(make(d, showCat)));
  holder.appendChild(frag);
}}

function visOf(d) {{
  return d.visibility || (d.shared ? 'shared' : 'private');
}}

function matchesAccess(d) {{
  if (S.access === 'all') return true;
  return visOf(d) === S.access;
}}

function updateShareStats() {{
  const tot = document.getElementById('statTotal');
  const pub = document.getElementById('statPublic');
  const sh = document.getElementById('statShared');
  if (tot) tot.textContent = String(DATA.length);
  if (pub) pub.textContent = String(DATA.filter(d => visOf(d) === 'public').length);
  if (sh) sh.textContent = String(DATA.filter(d => visOf(d) === 'shared').length);
}}

function setShareSync(msg, cls) {{
  const el = document.getElementById('shareSync');
  if (!el) return;
  el.textContent = msg || '';
  el.className = 'share-sync' + (cls ? ' ' + cls : '');
}}

async function loadCatalogue() {{
  setShareSync('catalogue…', 'loading');
  try {{
    const r = await fetch('/api/catalogue', {{
      credentials: 'same-origin',
      headers: {{ accept: 'application/json' }},
      cache: 'no-store',
    }});
    if (!r.ok) throw new Error('http_' + r.status);
    const data = await r.json();
    DATA = Array.isArray(data.items) ? data.items : [];
    TEAM = !!data.team;
    // The checkbox only exists for the team: an anonymous visitor has no API
    // that would accept the mutation, so offering it would be a dead control.
    document.body.classList.toggle('team', TEAM);
    if (TEAM) mountBatchBar();
    const login = document.getElementById('loginLink');
    const kicker = document.getElementById('headerKicker');
    const sub = document.getElementById('headerSub');
    if (TEAM) {{
      if (login) login.style.display = 'none';
      if (kicker) kicker.innerHTML = '<span class="header-kicker-dot" aria-hidden="true"></span>Équipe · Cloudflare Access';
      if (sub) sub.textContent = 'Toutes les pages. Publique = catalogue anonyme ; partagée = lien /s/… ; privée = Access.';
    }} else {{
      document.querySelectorAll('[data-k="access"][data-v="shared"],[data-k="access"][data-v="private"]').forEach(el => {{
        el.style.display = 'none';
      }});
    }}
    updateShareStats();
    render();
    setShareSync(TEAM ? 'équipe' : 'public', 'ok');
  }} catch (e) {{
    DATA = [];
    render();
    setShareSync('catalogue offline', 'err');
  }}
}}

function render() {{
  const q = S.q.toLowerCase().trim();
  let items = DATA.filter(matchesAccess);
  if (q) {{
    items = items.filter(d =>
        (d.t || '').toLowerCase().includes(q) ||
        (d.f || '').toLowerCase().includes(q) ||
        (d.cl || '').toLowerCase().includes(q) ||
        (d.desc || '').toLowerCase().includes(q) ||
        (d.slug || '').toLowerCase().includes(q));
  }}

  items.sort((a, b) => {{
    if (S.sort === 'date-desc') return (b.d||'').localeCompare(a.d||'') || (a.t||'').localeCompare(b.t||'');
    if (S.sort === 'date-asc')  return (a.d||'').localeCompare(b.d||'') || (a.t||'').localeCompare(b.t||'');
    return (a.t||'').localeCompare(b.t||'');
  }});

  // "Select all" and shift-range act on what the filter currently shows, not on
  // what happens to be drawn: batching means most of it is not in the DOM yet.
  VIEW = items;
  lastPick = -1;

  contentEl.innerHTML = '';

  if (!items.length) {{
    if (!DATA.length) {{
      contentEl.innerHTML = `<div class="empty">
        <p>Aucun artefact publié pour l’instant.</p>
        <p style="margin-top:8px">Publie un HTML avec <code>publish.sh</code> : il garde son chemin, par ex. <code>/lyra/visuals/architecture.html</code>.</p>
      </div>`;
    }} else {{
      contentEl.innerHTML = `<div class="empty">Aucun artefact ne correspond à « ${{escHtml(S.q)}} »</div>`;
    }}
    countEl.textContent = '0 résultat';
    return;
  }}

  // Groups become a queue of (section, items). Each batch drains it until the
  // budget is spent, so a group larger than one batch is split rather than
  // forcing the whole group into the DOM at once.
  const groups = [];
  if (S.group === 'starred') {{
    const starred = items.filter(d => stars.has(d.f));
    const rest    = items.filter(d => !stars.has(d.f));
    if (starred.length) groups.push(['★ Favoris', 'gold', starred, true]);
    if (rest.length)    groups.push(['Autres', 'neutral', rest, true]);
  }} else if (S.group === 'none') {{
    groups.push([null, null, items, true]);
  }} else if (S.group === 'cat') {{
    const bycat = groupByKey(items, d => d.cat);
    const cats = [...bycat.keys()].sort((a, b) => {{
      const maxDate = arr => arr.reduce((m, d) => (d.d || '') > m ? d.d : m, '');
      return maxDate(bycat.get(b)).localeCompare(maxDate(bycat.get(a)));
    }});
    cats.forEach(cat => {{
      const g = bycat.get(cat);
      groups.push([g[0].cl, g[0].c, g, false]);
    }});
  }} else {{
    const bydate = groupByKey(items, d => d.d || 'sans-date');
    const dates = [...bydate.keys()];
    if (S.sort === 'date-asc') dates.sort((a,b) => a.localeCompare(b));
    else dates.sort((a,b) => b.localeCompare(a));
    dates.forEach(date => {{
      groups.push([fmtDate(date === 'sans-date' ? '' : date), 'neutral', bydate.get(date), true]);
    }});
  }}

  startBatches(groups);

  countEl.textContent = items.length < DATA.length
    ? `${{items.length}} / ${{DATA.length}}`
    : `${{DATA.length}} artefact${{DATA.length!==1?'s':''}}`;
}}

// ── Batched rendering ─────────────────────────────────────────────────
const BATCH = 48;
let queue = [];
let sentinel = null;
let observer = null;

function startBatches(groups) {{
  if (observer) {{ observer.disconnect(); observer = null; }}
  queue = groups.map(([label, color, items, showCat]) => ({{
    label, color, items, showCat, at: 0, sec: null,
  }}));
  sentinel = document.createElement('div');
  sentinel.className = 'scroll-sentinel';
  sentinel.setAttribute('aria-hidden', 'true');
  contentEl.appendChild(sentinel);
  // No IntersectionObserver (old browser, or a test): render everything once
  // rather than hiding artefacts behind a scroll that never fires.
  if (typeof IntersectionObserver !== 'function') {{
    while (nextBatch()) {{}}
    return;
  }}
  observer = new IntersectionObserver(entries => {{
    if (entries.some(e => e.isIntersecting)) {{
      if (!nextBatch()) {{ observer.disconnect(); observer = null; sentinel.remove(); }}
    }}
  }}, {{ rootMargin: '800px 0px' }});
  observer.observe(sentinel);
  // Two batches up front so the first screen is full before any scroll.
  nextBatch();
  nextBatch();
}}

function nextBatch() {{
  let budget = BATCH;
  let drew = false;
  while (budget > 0 && queue.length) {{
    const g = queue[0];
    if (!g.sec) {{
      g.sec = mkSection(g.label, g.color, g.items.length, g.showCat);
      contentEl.insertBefore(g.sec, sentinel);
    }}
    const slice = g.items.slice(g.at, g.at + budget);
    if (slice.length) {{
      fillSection(g.sec, slice, g.showCat);
      g.at += slice.length;
      budget -= slice.length;
      drew = true;
    }}
    if (g.at >= g.items.length) queue.shift();
  }}
  if (!queue.length && sentinel) sentinel.remove();
  return drew;
}}

function applyTheme(t) {{
  html_el.setAttribute('data-theme', t);
  document.getElementById('themeBtn').textContent = t === 'dark' ? '🌙' : '☀️';
  localStorage.setItem(LS.theme, t);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', t === 'dark' ? '#0c0e16' : '#f5f2ec');
}}
document.getElementById('themeBtn').addEventListener('click', () => {{
  S.theme = S.theme === 'dark' ? 'light' : 'dark';
  applyTheme(S.theme);
}});

document.querySelectorAll('.seg').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const k = btn.dataset.k, v = btn.dataset.v;
    S[k] = v;
    localStorage.setItem(LS[k], v);
    document.querySelectorAll(`[data-k="${{k}}"]`).forEach(b => b.classList.toggle('on', b === btn));
    render();
  }});
}});

document.getElementById('search').addEventListener('input', e => {{ S.q = e.target.value; render(); }});

applyTheme(S.theme);
['group','sort','view','access'].forEach(k => {{
  document.querySelectorAll(`[data-k="${{k}}"]`).forEach(b => b.classList.toggle('on', b.dataset.v === S[k]));
}});
loadCatalogue();
document.addEventListener('visibilitychange', () => {{
  if (document.visibilityState === 'visible') loadCatalogue();
}});
window.addEventListener('focus', () => {{ loadCatalogue(); }});
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    items = load_items()
    manifest = to_manifest(items)
    # The tree publish owns manifest.json -- tree_snapshot writes it from the
    # SSOT, page by page. The landing is only a shell (its cards arrive from
    # GET /api/catalogue at runtime), so it can be emitted into the deploy
    # directory on its own. Writing the registry manifest there would replace
    # the snapshot's with an empty one and blank the catalogue.
    if len(args) == 2 and args[0] == "--shell-only":
        dest = Path(args[1])
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / "index.html"
        out.write_text(render(manifest), encoding="utf-8")
        print(f"✓ wrote {out} (shell)")
        return 0
    if args:
        print(f"usage: gen-index.py [--shell-only <dir>] — unknown: {' '.join(args)}", file=sys.stderr)
        return 2
    SITE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(manifest), encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"✓ wrote {OUT.relative_to(ROOT)} ({len(manifest)} items)")
    print(f"✓ wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
