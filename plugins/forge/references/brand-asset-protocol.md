# Brand Asset Protocol

> Extracted from huashu-design — "The essence of a brand is 'being recognized'"
> Core principle: **Assets > Specs** — Logo / product images / UI screenshots contribute far more to recognition than colors and fonts

---

## Trigger Conditions

Task involves a specific brand — user mentions product name / company name / explicit client (Stripe, Linear, Anthropic, Notion, DJI, your own company, etc.), regardless of whether the user proactively provided brand materials.

**Prerequisite**: Before running the protocol, confirm the brand/product exists and its status is known. If unsure whether product is released / specs / version, `WebSearch` to verify first.

---

## Asset Priority (sorted by recognition contribution)

| Asset Type | Recognition Contribution | Required |
|------------|-------------------------|----------|
| **Logo** | Highest — any brand with logo visible = instant recognition | **Required for ALL brands** |
| **Product images / renders** | Very high — physical product "protagonist" is the product itself | **Required for physical products (hardware / packaging / consumer goods)** |
| **UI screenshots / interface assets** | Very high — digital product "protagonist" is its interface | **Required for digital products (App / website / SaaS)** |
| **Color values** | Medium — auxiliary recognition, often collides without the above | Auxiliary |
| **Typography** | Low — needs to work with above to establish recognition | Auxiliary |
| **Mood keywords** | Low — for agent self-check | Auxiliary |

### Translation to Execution Rules

- Only extracting colors + fonts, not finding logo / product images / UI → **Violates this protocol**
- Using CSS silhouette / hand-drawn SVG instead of real product image → **Violates this protocol**
- Can't find assets but don't tell user or use AI generation, just forge ahead → **Violates this protocol**
- Better to stop and ask user for assets than fill with generic content

---

## 5-Step Hard Protocol

### Step 1 — Ask (asset checklist, all at once)

Don't just ask "Do you have brand guidelines?" — too vague, user won't know what to provide. Ask by checklist item:

```
Regarding <brand/product>, which of these materials do you have? Listed by priority:
1. Logo (SVG / high-res PNG) — required for any brand
2. Product images / official renders — required for physical products
3. UI screenshots / interface assets — required for digital products
4. Color values list (HEX / RGB / brand color palette)
5. Typography list (Display / Body)
6. Brand guidelines PDF / Figma design system / brand website link

Send what you have, I'll search/scrape/generate what you don't.
```

### Step 2 — Search Official Channels (by asset type)

| Asset | Search Paths |
|-------|--------------|
| **Logo** | `<brand>.com/brand` · `<brand>.com/press` · `<brand>.com/press-kit` · `brand.<brand>.com` · Website header inline SVG |
| **Product images / renders** | `<brand>.com/<product>` product page hero image + gallery · Official YouTube launch film frame captures · Official press release images |
| **UI screenshots** | App Store / Google Play product page screenshots · Website screenshots section · Product demo video frame captures |

`WebSearch` fallback keywords:
- Logo not found → `<brand> logo download SVG`, `<brand> press kit`
- Product images not found → `<brand> <product> official renders`, `<brand> <product> product photography`
- UI not found → `<brand> app screenshots`, `<brand> dashboard UI`

### Step 3 — Download Assets (3 fallback paths per asset type)

#### 3.1 Logo (required for any brand)

Three paths in decreasing success rate:
1. **Standalone SVG/PNG file** (ideal):
   ```bash
   curl -o assets/<brand>-brand/logo.svg https://<brand>.com/logo.svg
   curl -o assets/<brand>-brand/logo-white.svg https://<brand>.com/logo-white.svg
   ```
2. **Extract inline SVG from website HTML** (used in 80% of cases):
   ```bash
   curl -A "Mozilla/5.0" -L https://<brand>.com -o assets/<brand>-brand/homepage.html
   # Then grep <svg>...</svg> to extract logo node
   ```
3. **Official social media avatar** (last resort): GitHub / Twitter / LinkedIn company avatars are usually 400×400 or 800×800 transparent PNG

#### 3.2 Product Images / Renders (required for physical products)

By priority:
1. **Official product page hero image** (highest priority): Right-click to get image URL / curl fetch. Resolution usually 2000px+
2. **Official press kit**: `<brand>.com/press` often has high-res product image downloads
3. **Official launch video frame capture**: Use `yt-dlp` to download YouTube video, ffmpeg to extract a few high-res frames
4. **Wikimedia Commons**: Public domain often has images
5. **AI generation fallback**: Use real product image as reference for AI to generate variants matching animation scene. **Do NOT use CSS/SVG hand-drawn substitute**

#### 3.3 UI Screenshots (required for digital products)

- App Store / Google Play product screenshots (note: may be mockups not real UI, compare carefully)
- Website screenshots section
- Product demo video frame captures
- Product official Twitter/X release screenshots (often latest version)
- If user has account, directly screenshot real product interface

#### 3.4 Asset Quality Threshold "5-10-2-8" Principle

> **Logo rules differ from other assets**. If logo exists, must use it (if not, stop and ask user); other assets follow "5-10-2-8" quality threshold.

| Dimension | Standard | Anti-pattern |
|-----------|----------|--------------|
| **5 search rounds** | Cross-search multiple channels, don't stop after grabbing first 2 results | Use first page results directly |
| **10 candidates** | At least gather 10 alternatives before filtering | Only grab 2, no choice |
| **Select 2 good ones** | Carefully pick 2 from 10 as final assets | Use all = visual overload |
| **Each 8/10+ score** | Below 8 points **better not use**, use honest placeholder | Stuff 7-point assets into brand-spec.md |

**8/10 Scoring Dimensions** (record in `brand-spec.md` when scoring):

1. **Resolution** · ≥2000px (print/large screen scenarios ≥3000px)
2. **Copyright clarity** · Official source > Public domain > Free assets > Suspected stolen
3. **Brand mood fit** · Consistent with mood keywords
4. **Lighting / composition / style consistency** · 2 assets together don't clash
5. **Independent narrative ability** · Can express a narrative role alone (not decoration)

### Step 4 — Verify + Extract

| Asset | Verification Action |
|-------|---------------------|
| **Logo** | File exists + SVG/PNG opens + at least two versions (for dark/light backgrounds) + transparent background |
| **Product images** | At least one 2000px+ resolution + clean background or transparent + multiple angles |
| **UI screenshots** | Real resolution (1x / 2x) + is latest version + no user data contamination |
| **Color values** | `grep -hoE '#[0-9A-Fa-f]{6}' assets/<brand>-brand/*.{svg,html,css} | sort | uniq -c | sort -rn | head -20`, filter black/white/gray |

**Beware demo brand pollution**: Product screenshots often contain demo brand colors (e.g., a tool screenshot demoing Hey Tea red), that's not the tool's color. **When two strong colors appear simultaneously, must distinguish**.

**Brand multiple facets**: Same brand's website marketing colors and product UI colors often differ. **Both are real** — choose appropriate facet based on delivery scenario.

### Step 5 — Solidify as `brand-spec.md` File

```markdown
# <Brand> · Brand Spec
> Collection date: YYYY-MM-DD
> Asset sources: <list download sources>
> Asset completeness: <complete / partial / inferred>

## 🎯 Core Assets (first-class citizens)

### Logo
- Main version: `assets/<brand>-brand/logo.svg`
- Light background inverse: `assets/<brand>-brand/logo-white.svg`
- Usage scenarios: <intro/outro/corner watermark/global>
- Forbidden transformations: <no stretch/color change/add stroke>

### Product Images (required for physical products)
- Main view: `assets/<brand>-brand/product-hero.png` (2000×1500)
- Detail shots: `assets/<brand>-brand/product-detail-1.png`
- Scene shots: `assets/<brand>-brand/product-scene.png`
- Usage scenarios: <close-up/rotation/comparison>

### UI Screenshots (required for digital products)
- Home: `assets/<brand>-brand/ui-home.png`
- Core features: `assets/<brand>-brand/ui-feature-<name>.png`
- Usage scenarios: <product showcase/Dashboard reveal/comparison demo>

## 🎨 Auxiliary Assets

### Color Palette
- Primary: #XXXXXX  <source annotation>
- Background: #XXXXXX
- Ink: #XXXXXX
- Accent: #XXXXXX
- Forbidden colors: <brand explicitly doesn't use these color families>

### Typography
- Display: <font stack>
- Body: <font stack>
- Mono (for data HUD): <font stack>

### Signature Details
- <Which details are "done at 120%">

### Forbidden Zones
- <Explicitly cannot do: e.g., Stripe doesn't use low-saturation warm colors>

### Mood Keywords
- <3-5 adjectives>
```

**Execution Discipline After Writing Spec (hard requirement)**:
- All HTML must **reference** asset file paths from `brand-spec.md`, not allowed to use CSS silhouette / hand-drawn SVG substitute
- Logo as `<img>` referencing real file, not redrawn
- Product images as `<img>` referencing real files, not CSS silhouette substitute
- CSS variables injected from spec: `:root { --brand-primary: ...; }`, HTML only uses `var(--brand-*)`

---

## Fallback for Full Protocol Failure

Handle by asset type:

| Missing | Handling |
|---------|----------|
| **Logo completely not found** | **Stop and ask user**, don't forge ahead (logo is foundation of brand recognition) |
| **Product images (physical product) not found** | Priority: AI generation (using official reference as base) → Second: ask user → Last resort: honest placeholder (gray block + text label, clearly marked "product image pending") |
| **UI screenshots (digital product) not found** | Ask user for their own account screenshot → Official demo video frame capture. Don't use mockup generator to fill |
| **Color values completely not found** | Go with "Design Direction Advisor mode", recommend 3 directions to user with assumption annotations |

**Forbidden**: Silently using CSS silhouette / generic gradients when assets can't be found — this is the protocol's biggest anti-pattern. **Better to stop and ask than to make do**.

---

## Protocol Cost vs Non-Protocol Cost

| Scenario | Time |
|----------|------|
| Correctly complete protocol | Download logo 5 min + Download 3-5 product images/UI 10 min + grep colors 5 min + Write spec 10 min = **30 minutes** |
| Skip protocol cost | Produce unrecognizable generic animation → User rework 1-2 hours, or even redo |

**This is the cheapest investment in stability**. Especially for commercial projects / launch events / important client projects, 30 minutes of asset protocol is insurance money.
