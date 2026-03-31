# FigX

Translate Figma designs and publish them to X/Twitter — powered by Claude Code + MCP.

FigX automates the workflow of taking visual content in one language, translating it, overlaying translated text in Figma, and publishing it as an X thread or single tweet.

---

## How It Works

```
figx publish <figma-link>

  1. Read text from Figma design
  2. Translate (source language -> target language)
  3. Overlay translated text in Figma
  4. Export PNG images
  5. Auto-verify each page
  6. Plan thread structure + write copy
  7. [You review the preview]
  8. Publish to X
```

Only **one human approval step** — everything else is automated.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-username/figx.git
cd figx

# 2. Set up credentials
cp .env.example .env        # Add your X API keys
cp config.example.json config.json  # Customize settings

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure MCP servers (see SETUP.md)

# 5. Add skill to Claude Code
# Then use: figx translate <figma-link>
```

See [SETUP.md](SETUP.md) for detailed setup instructions.

---

## Commands

| Command | What it does |
|---------|-------------|
| `figx translate <link>` | Translate + overlay + export PNG |
| `figx publish <link>` | Full pipeline: translate -> thread -> publish |
| `figx export <link>` | Export already-translated pages as PNG |
| `figx publish --local <dir>` | Publish from local images (skip translation) |
| `figx check <description>` | Evaluate content fitness for X |
| `figx log` | View publishing history |

---

## Configuration

`config.json` controls the entire pipeline:

- **translation** — Source/target language, tone, character ratio, preserved terms
- **overlay** — Margin and gap constraints for text placement
- **thread** — Structure template, character limit, CTA text
- **brand** — Your brand name, X handle, name mappings
- **output** — Export directory, image scale, archive path

See [config.example.json](config.example.json) for all options.

---

## Standalone Publishing

`publish.py` works independently of Claude Code:

```bash
# Preview without posting
python3 publish.py thread.json --dry-run

# Publish
python3 publish.py thread.json

# With custom config
python3 publish.py thread.json --config my-config.json
```

See [examples/thread.example.json](examples/thread.example.json) for the expected format.

---

## Architecture

FigX relies on three MCP (Model Context Protocol) servers:

| Server | Purpose |
|--------|---------|
| [Figma MCP](https://mcp.figma.com) | Read/write text nodes in Figma |
| [figma-mcp-full-server](https://www.npmjs.com/package/figma-mcp-full-server) | Export PNG images |
| [x-mcp](https://github.com/Infatoshi/x-mcp) | Post tweets and upload media |

The `skill.md` file orchestrates these tools through Claude Code, while `publish.py` provides a standalone CLI for the publishing step.

---

## Overlay Constraints

Text overlay follows 8 hard rules (each learned from production bugs):

1. Match by node ID only (never by text content)
2. Hide original node before overlaying
3. Width capped at `frame_width - node.x - 4px`
4. Minimum 8px gap between neighboring overlays
5. Never overlap non-text elements (images, vectors)
6. Skip nodes already in the target language
7. Mixed font sizes use the midpoint value
8. Auto collision detection after every write

---

## Known Limitations

- X Free tier: 1,500 tweets/month
- Programmatic replies restricted on Free tier (since Feb 2026) — threads may need Basic/Pro
- Figma MCP beta has call-rate limits
- Image uploads require OAuth 1.0a (tweepy v1.1 API)

---

## License

[MIT](LICENSE)
