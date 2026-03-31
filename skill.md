# FigX Skill — Figma Translation + X Publishing

> Translate text in Figma designs and publish as X/Twitter threads.
> This is a Claude Code skill file. Add it to your project with `/add-skill`.

---

## Triggers

| Command | Mode | Description |
|---------|------|-------------|
| `figx translate <figma-link>` | Translate only | Translate + overlay + export PNG |
| `figx publish <figma-link>` | Full pipeline | Translate + export + thread + publish |
| `figx export <figma-link>` | Export only | Export translated pages as PNG |
| `figx publish --local <dir>` | Local mode | Skip translation, use existing images |
| `figx check <description>` | Evaluate | Score content for X fitness |
| `figx log` | Query | Show published.log |

---

## Prerequisites

Before first run, verify:
1. `config.json` exists in the project root (copy from `config.example.json`)
2. `.env` exists with X API credentials (copy from `.env.example`)
3. Three MCP servers configured (see `SETUP.md`):
   - `figma` — Official Figma Remote MCP (read/write text)
   - `figma-export` — figma-mcp-full-server (export PNG)
   - `x-twitter` — Infatoshi/x-mcp (post tweets + upload media)
4. Python dependencies installed: `pip install -r requirements.txt`

Load config at start of every run:
```
Read config.json -> store as CONFIG
```

---

## Core Principle: Minimum Confirmation, Maximum Automation

The entire pipeline has **exactly 1 human confirmation point** — the thread preview before publishing.

```
User provides Figma link
       |
       v
[AUTO] Phase 1: Translate + Overlay + Export
       |
       v
[AUTO] Phase 1.5: Self-check (verify each exported page)
       |  <- auto-fix issues, do not ask user
       v
[AUTO] Phase 2: Plan thread + select images + validate char count
       |
       v
[SHOW] Full thread preview (text + image assignments)
       |
       v
[WAIT] User confirms -> Phase 3: Publish
```

---

## Phase 1: Translate + Overlay

### Step 1: Pre-analysis (MANDATORY before any overlay code)

Use `use_figma` to extract all text nodes from every top-level frame:

```javascript
// Extract text node data from all frames
const frames = figma.currentPage.children.filter(n => n.type === "FRAME");
const result = frames.map(frame => ({
  frame_id: frame.id,
  frame_name: frame.name,
  frame_width: frame.width,
  texts: frame.findAll(n => n.type === "TEXT").map(t => ({
    id: t.id,
    characters: t.characters,
    x: t.x,
    y: t.y,
    width: t.width,
    height: t.height,
    fontSize: t.fontSize,        // may be "mixed" (Symbol)
    fontStyle: t.fontName?.style, // may be "mixed"
    fills: t.fills
  }))
}));
return JSON.stringify(result);
```

### Step 2: Classify nodes

For each text node, classify:
- **translate**: Contains source language characters (per `CONFIG.translation.source_language`)
- **skip**: Pure target language text (e.g., "CPU", "GPU", numbers) — do NOT create overlay
- **special**: Mixed fontSize — use a single middle fontSize value

Build a `nodeID -> translation` mapping.

### Step 3: Translate

Apply rules from `CONFIG.translation`:
- **Tone**: from `CONFIG.translation.tone`
- **Target language**: from `CONFIG.translation.target_language`
- **Length**: target language chars <= source chars x `CONFIG.translation.char_ratio`
- **Lines**: do not exceed original line count x `CONFIG.translation.max_lines_ratio` (default 1.0)
- **Terms**: preserve items in `CONFIG.translation.preserve_terms`
- **Brand**: apply `CONFIG.brand.name_mappings` (e.g., source brand name -> target brand name)
- **Handle**: use `CONFIG.brand.x_handle` when referencing the X account

### Step 4: Write overlays to Figma

**8 hard constraints (non-configurable — each prevents a known production bug):**

1. **Node ID matching only** — NEVER match by text content. Use the node ID from pre-analysis.
2. **Hide original** — Set `node.visible = false` on the source text node.
3. **Width constraint** — `max_w = frame_width - node.x - CONFIG.overlay.right_margin_px` (default 4px). Prevents right-edge clipping.
4. **Neighbor collision** — `overlay.x + overlay.width < neighbor.x - CONFIG.overlay.neighbor_gap_px` (default 8px). Prevents overlap with adjacent nodes.
5. **Non-text protection** — Do not let overlay intrude into x-region of non-text elements (images, vectors).
6. **Skip target-language nodes** — Do not create overlay for nodes classified as "skip".
7. **Mixed fontSize** — Use the midpoint of min/max fontSize values in the node.
8. **Font** — Use `CONFIG.overlay.font_family` (default: Inter) with styles from `CONFIG.overlay.font_styles` (default: Regular / Bold).

After writing all overlays, run automatic **collision detection**:
```javascript
// Check for overlay collisions
const overlays = figma.currentPage.findAll(n => n.name.startsWith('overlay_'));
const collisions = [];
for (let i = 0; i < overlays.length; i++) {
  for (let j = i + 1; j < overlays.length; j++) {
    const a = overlays[i], b = overlays[j];
    // Same parent frame check
    if (a.parent?.id !== b.parent?.id) continue;
    const gap = Math.abs((a.x + a.width) - b.x);
    if (gap < 8) collisions.push({a: a.id, b: b.id, gap});
  }
}
return JSON.stringify(collisions);
```

If collisions found, auto-fix by reducing fontSize or width. Do not ask user.

### Step 5: Export PNG

Use `figma-export` MCP to export each frame at `CONFIG.output.image_scale` (default 2x).

Save to `CONFIG.output.export_dir` with naming pattern from `CONFIG.output.image_naming`.

---

## Phase 1.5: Self-check (Automatic)

For each exported PNG, verify:
- All visible text is in target language (no source language remaining)
- Text is not clipped by frame boundaries
- No title/body text overlap
- Line breaks are at natural positions

**Auto-fix any issues found:**
- Source language visible -> check for missed node ID mapping
- Text clipped -> reduce overlay width
- Overlap -> reduce fontSize
- Re-export only affected pages

Proceed to Phase 2 only when all pages pass.

---

## Phase 2: Thread Planning

### Decide: single tweet or thread

- Total images <= 4 -> **single tweet** (one post with all images)
- Total images > 4 -> **thread** (multiple tweets linked as replies)

### Thread structure

Use `CONFIG.thread.structure` as the template. Default:
```
Tweet 1 [HOOK]:  Data shock + problem definition (2 images)
Tweet 2 [CORE]:  Technical breakthrough + surprising result (2 images)
Tweet 3 [DEPTH]: Industry value + broader perspective (2 images)
Tweet 4 [CLOSE]: Punchline + CTA (1-2 images)
```

### Copy rules

- Tweet 1 must open with a data point or counter-intuitive fact (hook)
- Every tweet <= `CONFIG.thread.max_chars` (default 280) characters
- Max `CONFIG.thread.max_tweets` (default 25) tweets per thread
- Short paragraphs, frequent line breaks
- Last tweet: source attribution + `CONFIG.thread.cta` + `CONFIG.thread.signature` (if set)
- Tweet 1 ends with thread indicator if `CONFIG.thread.thread_emoji` is true
- Max 1-2 emoji per tweet

### Auto char-count validation

After writing each tweet, verify `len(text) <= max_chars`. If over:
1. Remove paper citation line
2. Shorten CTA
3. Compress bullet points

### Image selection priority

1. Hook page (required): key data visualization
2. Metaphor page (high priority): strong visual impact
3. Core finding page (required): critical data
4. Overview/summary page (recommended)
5. Signature page (last)

### Output

Save to `CONFIG.output.export_dir/{topic}/`:
- Images named per `CONFIG.output.image_naming`
- `thread.json` (for `publish.py`)
- `thread_preview.md` (human-readable preview)

---

## Phase 2.5: Human Confirmation (ONLY wait point)

Display the complete thread preview:
- Full text of each tweet with character count
- Image assignments for each tweet
- Total tweet count and mode (single/thread)

**Wait for user to confirm before proceeding.**

---

## Phase 3: Publish

### Option A: Via publish.py (recommended)

```bash
# Dry run first
python3 publish.py thread.json --dry-run

# If OK, publish
python3 publish.py thread.json
```

### Option B: Via x-twitter MCP

Use MCP tools directly:
1. `upload_media` for each image -> collect media_ids
2. `post_tweet` for first tweet (with media_ids)
3. `reply_to_tweet` for subsequent tweets (threading)

### Error recovery

- 403 on single tweet: wait 5s -> retry
- Image upload failure: retry once
- Rate limit: wait and retry
- Thread reply restriction (X Free tier): warn user, suggest upgrading

### Post-publish

- Log to `published.log` in CWD
- Archive `thread.json` to `CONFIG.output.archive_dir`
- Return thread URL

---

## Local Mode (`figx publish --local <dir>`)

Skip Phase 1 entirely. Expects:
- A directory with pre-exported PNG images
- Directly enter Phase 2 (thread planning) using the images in the directory

---

## Ad Mode

When publishing sponsored content:
- Soften promotional language to tech-review style
- Include `#ad` or `#sponsored` tag
- Do not include discount codes or promo links

---

## Content Fitness Evaluation (`figx check`)

Five dimensions (weighted score):
1. **Timeliness** (30%): How current is the topic?
2. **Platform fit** (25%): Does it match X audience expectations?
3. **Visual uniqueness** (20%): How distinctive are the visuals?
4. **Competitive edge** (15%): What makes this stand out?
5. **Adaptability** (10%): How easy to adapt for translation?

Rating: >= 4.0 green | 3.0-3.9 yellow | 2.0-2.9 orange | < 2.0 red

---

## MCP Tool Dependencies

| MCP Server | Purpose | Key Tools Used |
|-----------|---------|---------------|
| `figma` | Read/write text in Figma | `use_figma`, `get_screenshot`, `get_metadata` |
| `figma-export` | Export PNG from Figma | `get_figma_image`, `export_multiple_images` |
| `x-twitter` | Post to X/Twitter | `post_tweet`, `reply_to_tweet`, `upload_media` |

---

## Known Limitations

- X Free tier: 1,500 tweets/month
- X restricts programmatic replies (since Feb 2026) — thread publishing may require Basic/Pro tier
- Figma MCP beta: free but has call-rate limits (Starter plan: ~6 calls/min)
- Image upload requires tweepy v1.1 API (OAuth 1.0a)
- Inter font must be available in the Figma file for overlays
