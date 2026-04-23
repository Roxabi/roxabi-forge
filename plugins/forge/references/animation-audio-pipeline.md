# Animation Audio Pipeline

> Extracted from huashu-design — Video export + SFX + BGM pipeline
> For: roxabi-production (animation post-processing)
> Status: Reference document — implementation TBD in roxabi-production

---

## Pipeline Overview

```
HTML Animation (25fps base)
    │
    ├── render-video.js → MP4 (video only)
    │       │
    │       └── convert-formats.sh → 60fps MP4 + GIF
    │
    └── add-music.sh → Final MP4 (video + audio)
            │
            ├── BGM track (from 6 scene-based tracks)
            └── SFX layer (from 37 cue sounds)
```

---

## 1. Video Recording — `render-video.js`

### Purpose
Record HTML animation to 25fps MP4 via Playwright.

### Key Requirements for HTML Animation

The HTML must implement these signals for clean recording:

```js
// State variables
let time = 0;
let playing = false;      // Default off until fonts ready
let lastTick = null;       // Sentinel — first frame dt = 0

// Tick function
function tick(now) {
  if (lastTick === null) {
    lastTick = now;
    window.__ready = true; // ← Recording anchor (sync with t=0)
    render(0);
    requestAnimationFrame(tick);
    return;
  }
  const dt = (now - lastTick) / 1000;
  lastTick = now;

  if (playing) {
    let t = time + dt;
    if (t >= DURATION) {
      // Loop control — detect recording mode
      t = window.__recording ? DURATION - 0.001 : 0;
      if (!window.__recording) fired.clear();
    }
    time = t;
    render(time);
  }
  requestAnimationFrame(tick);
}

// Boot sequence — wait for fonts
document.fonts.ready.then(() => {
  render(0);
  playing = true;
  requestAnimationFrame(tick);
});

// Seek interface (for video script to align time)
window.__seek = (t) => { fired.clear(); time = t; lastTick = null; render(t); };
```

### Recording Script Pattern

```js
// Phase 1: Warmup (throwaway context)
const warmupCtx = await browser.newContext({ viewport });
const warmupPage = await warmupCtx.newPage();
await warmupPage.goto(url, { waitUntil: 'networkidle' });
await warmupPage.waitForTimeout(1200);
await warmupCtx.close();

// Phase 2: Record (fresh context)
const recordCtx = await browser.newContext({
  viewport,
  recordVideo: { dir: tmpDir }
});
// Inject recording signal BEFORE page load
await recordCtx.addInitScript(() => { window.__recording = true; });

const page = await recordCtx.newPage();
await page.goto(url, { waitUntil: 'networkidle' });

// Wait for animation ready signal
await page.waitForFunction(() => window.__ready === true);

// Optional: defensive seek to t=0
await page.evaluate(() => window.__seek && window.__seek(0));

// Record duration
await page.waitForTimeout(DURATION * 1000);
await page.close();
await recordCtx.close();

// Video is now written to tmpDir
```

### Chrome Element Hiding

Inject CSS to hide player chrome (progress bar, replay button, etc.):

```js
await recordCtx.addInitScript(() => {
  const style = document.createElement('style');
  style.textContent = `
    .progress, .counter, .phases, .replay, .masthead, .footer,
    .no-record, [data-role="chrome"] { display: none !important; }
  `;
  document.head.appendChild(style);
});
```

---

## 2. Format Conversion — `convert-formats.sh`

### 25fps → 60fps

**Default (compatible)**: Frame copy
```bash
ffmpeg -i input.mp4 -vf "fps=60" -c:v libx264 -profile:v high -level 4.0 output-60fps.mp4
```

**High-quality (less compatible)**: Motion interpolation
```bash
ffmpeg -i input.mp4 -vf "minterpolate=fps=60:mi_mode=mci" -c:v libx264 output-60fps-mci.mp4
```

> **Warning**: minterpolate output may fail on QuickTime/Safari. Test target players before using.

### MP4 → GIF (palette-optimized)

Two-pass palette for better color fidelity:

```bash
ffmpeg -i input.mp4 -vf "palettegen" palette.png
ffmpeg -i input.mp4 -i palette.png -lavfi "paletteuse" output.gif
```

For longer animations, add `stats_mode=diff`:

```bash
ffmpeg -i input.mp4 -vf "palettegen=stats_mode=diff" palette.png
ffmpeg -i input.mp4 -i palette.png -lavfi "paletteuse=dither=bayer:bayer_scale=5" output.gif
```

---

## 3. Audio Pipeline — Dual-Track System

### Concept: BGM + SFX

| Track | Purpose | Frequency | Volume |
|-------|---------|-----------|--------|
| **BGM** | Emotional foundation, pacing guide | Low (bass, pads) | -14 to -12 LUFS |
| **SFX** | UI feedback, transitions, emphasis | High (clicks, whooshes) | -20 to -18 LUFS |

**Golden ratio**: BGM 6-8dB louder than SFX. SFX sits "on top" without competing.

### BGM Library (6 tracks)

| Track | Scene | BPM | Character |
|-------|-------|-----|-----------|
| `bgm-tech.mp3` | Product launch, hero demo | 120-130 | IDM, minimal tech, precise |
| `bgm-ad.mp3` | Marketing, announcement | 90-100 | Upbeat, emotional swell |
| `bgm-educational.mp3` | Tutorial, explainers | 85-95 | Calm, steady, clear |
| `bgm-educational-alt.mp3` | Tutorial variant | 80-90 | Ambient, softer |
| `bgm-tutorial.mp3` | Step-by-step guides | 75-85 | Gentle, supportive |
| `bgm-tutorial-alt.mp3` | Tutorial variant | 70-80 | Lo-fi hip-hop feel |

### SFX Library (37 cues by category)

| Category | Files | Usage |
|----------|-------|-------|
| **UI Click** | `ui-click-*.mp3` (8) | Button press, toggle, select |
| **Transition** | `whoosh-*.mp3`, `swoosh-*.mp3` (6) | Panel reveal, scene cut |
| **Success** | `success-*.mp3`, `ding-*.mp3` (5) | Task complete, positive feedback |
| **Error** | `error-*.mp3`, `buzz-*.mp3` (4) | Invalid action, warning |
| **Data** | `pop-*.mp3`, `blip-*.mp3` (6) | Data point appear, chart build |
| **Typing** | `key-*.mp3`, `type-*.mp3` (5) | Text reveal, input |
| **Camera** | `shutter-*.mp3`, `zoom-*.mp3` (3) | Screenshot, zoom action |

### Scene Recipes (SFX Density)

| Scene Type | SFX/10s | Pattern |
|------------|---------|---------|
| **Launch hero** | ~6 | Every beat has a cue |
| **Tool demo** | 0-2 | Minimal, BGM carries |
| **Tutorial** | 2-4 | Per UI interaction |
| **Comparison** | 3-5 | Per transition |

### ffmpeg Mix Template

```bash
# Mix BGM + SFX with proper levels
ffmpeg -i video.mp4 \
  -i bgm-track.mp3 \
  -i sfx-layer.mp3 \
  -filter_complex "\
    [1:a]volume=-4dB,afade=t=in:st=0:d=1,afade=t=out:st=14:d=2[bgm]; \
    [2:a]volume=-12dB[sfx]; \
    [bgm][sfx]amix=inputs=2:duration=longest[aout]" \
  -map 0:v -map "[aout]" \
  -c:v copy -c:a aac \
  output-with-audio.mp4
```

**SFX cue timing**: Build a cue list with timestamps, concatenate SFX files at those positions:

```bash
# Generate silent base at correct length
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 15 sfx-base.mp3

# Overlay cues at specific times
ffmpeg -i sfx-base.mp3 \
  -i sfx/click-01.mp3 -i sfx/whoosh-02.mp3 -i sfx/success-01.mp3 \
  -filter_complex "\
    [0:a]atrim=0:15[sfx]; \
    [sfx][1:a]adelay=1200|1200[s1]; \
    [s1][2:a]adelay=3500|3500[s2]; \
    [s2][3:a]adelay=14000|14000[out]" \
  -map "[out]" sfx-layer.mp3
```

---

## 4. ffmpeg Command Reference

### Verify Audio Stream

```bash
ffprobe -select_streams a -show_entries stream=codec_name -of csv=p=0 video.mp4
# Should output: aac (or mp3, etc.)
# Empty = no audio stream
```

### Extract Frame at Time

```bash
# First frame
ffmpeg -i video.mp4 -ss 0 -vframes 1 frame-0.png

# Last frame
ffmpeg -i video.mp4 -ss 19.8 -vframes 1 frame-end.png
```

### Trim Head

If video has pre-animation blank frames:

```bash
ffmpeg -ss 0.3 -i video.mp4 -c copy trimmed.mp4
```

---

## 5. Audio Design Rules (from huashu-design)

### 5.1 SFX pitch to BGM scale

Match SFX frequency to BGM key. If BGM is in C minor, avoid SFX with strong E natural.

### 5.2 Avoid these anti-patterns

| Anti-pattern | Issue | Fix |
|--------------|-------|-----|
| Every frame has SFX | Audio fatigue | Space cues with silence |
| Same SFX repeated | Annoying repetition | Vary with pitch/timing |
| SFX louder than BGM | BGM drowned out | Adjust levels |
| No fade in/out on BGM | Abrupt start/end | Add 1s fade in, 2s fade out |

### 5.3 Recipe A (Apple Keynote style)

- SFX density: High (~0.4/s)
- SFX pitch: Matched to BGM scale
- BGM: IDM / minimal tech
- Ending: Logo reveal + single tone + abrupt hold

### 5.4 Recipe B (Tool demo style)

- SFX density: Zero (BGM only)
- BGM: Lo-fi hip-hop, 85-90 BPM
- Interaction timing: Key UI actions on kick/snare beats

### 5.5 Recipe C (Office narrative style)

- SFX density: Medium (~0.3/s)
- SFX type: UI clicks, toggles
- BGM: Jazzy instrumental, minor key
- Highlight: One 3D pop-out moment

---

## 6. Asset Locations (huashu-design)

| Asset | Path |
|-------|------|
| BGM tracks | `assets/bgm-*.mp3` |
| SFX library | `assets/sfx/<category>/*.mp3` |
| Render script | `scripts/render-video.js` |
| Convert script | `scripts/convert-formats.sh` |
| Audio mix script | `scripts/add-music.sh` |

---

## 7. Integration Notes for roxabi-production

### Recommended approach

1. **Copy SFX/BGM assets** to `roxabi-production/assets/audio/`
2. **Port scripts** to `roxabi-production/scripts/`
3. **Create audio manifest** similar to huashu-design's asset structure
4. **Document scene recipes** per project type

### Not needed for forge

Forge produces static HTML artifacts. Audio pipeline is for post-processing animation exports, which falls under roxabi-production scope.

---

**Version**: 1.0
**Source**: huashu-design SKILL.md + references/video-export.md + references/audio-design-rules.md + references/sfx-library.md
**Created**: 2026-04-23
