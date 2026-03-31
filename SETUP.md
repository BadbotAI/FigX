# FigX Setup Guide

Step-by-step instructions to get FigX running.

---

## 1. X/Twitter API Credentials

1. Go to [X Developer Portal](https://developer.x.com/en/portal/dashboard)
2. Create a project and app (Free tier works for basic usage)
3. Under **Keys and tokens**, generate:
   - API Key + Secret (Consumer Keys)
   - Access Token + Secret
   - Bearer Token
4. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your keys
```

> **Note:** Image uploads require OAuth 1.0a (v1.1 API). Make sure your app has **Read and Write** permissions. Thread publishing (self-replies) may require Basic or Pro tier due to X API restrictions introduced in Feb 2026.

---

## 2. Figma Token

1. In Figma, go to **Settings > Security > Personal access tokens**
2. Generate a new token with read/write scope
3. Save it — you'll need it for the `figma-export` MCP server config

For the official Figma MCP (`figma` server), authentication happens via browser OAuth when you first connect. No manual token needed.

---

## 3. Install MCP Servers

FigX requires three MCP servers configured in Claude Code.

### 3a. Official Figma MCP (read/write text)

Add to your Claude Code MCP config:
```json
{
  "figma": {
    "type": "url",
    "url": "https://mcp.figma.com/mcp"
  }
}
```

This uses Figma's official Remote MCP. You'll authorize via browser on first use.

### 3b. figma-export (export PNG)

```json
{
  "figma-export": {
    "command": "npx",
    "args": ["-y", "figma-mcp-full-server"],
    "env": {
      "FIGMA_PERSONAL_ACCESS_TOKEN": "<your-figma-pat>"
    }
  }
}
```

Requires Node.js. The PAT is the token from Step 2.

### 3c. x-twitter MCP (post tweets)

Install the [Infatoshi/x-mcp](https://github.com/Infatoshi/x-mcp) server:

```bash
git clone https://github.com/Infatoshi/x-mcp.git
cd x-mcp
npm install && npm run build
```

Add to your MCP config:
```json
{
  "x-twitter": {
    "command": "node",
    "args": ["/path/to/x-mcp/dist/index.js"],
    "env": {
      "X_API_KEY": "<your-key>",
      "X_API_SECRET": "<your-secret>",
      "X_ACCESS_TOKEN": "<your-token>",
      "X_ACCESS_TOKEN_SECRET": "<your-token-secret>",
      "X_BEARER_TOKEN": "<your-bearer>"
    }
  }
}
```

See `mcp-config.example.json` for a complete example.

---

## 4. Python Dependencies

```bash
pip install -r requirements.txt
```

This installs `tweepy` for direct publishing via `publish.py`.

---

## 5. Configure FigX

```bash
cp config.example.json config.json
```

Edit `config.json` to match your workflow:

| Section | Key fields |
|---------|-----------|
| `translation` | `source_language`, `target_language`, `tone`, `char_ratio`, `preserve_terms`, `max_lines_ratio` |
| `overlay` | `font_family`, `font_styles`, `right_margin_px`, `neighbor_gap_px` |
| `thread` | `structure`, `max_chars`, `max_tweets`, `cta`, `signature`, `thread_emoji` |
| `brand` | `name`, `x_handle`, `name_mappings` |
| `output` | `export_dir`, `image_scale`, `image_naming`, `archive_dir` |

---

## 6. Add the Skill to Claude Code

```bash
# From your project directory
claude /add-skill /path/to/FigX/skill.md
```

Or copy `skill.md` into your project's `.claude/skills/` directory.

---

## 7. Verification Checklist

Run through this checklist to confirm everything works:

- [ ] `.env` has all 5 X API credentials
- [ ] `config.json` exists with your settings
- [ ] `figma` MCP responds (try: ask Claude to read a Figma file)
- [ ] `figma-export` MCP responds (try: export a PNG)
- [ ] `x-twitter` MCP responds (try: `get_user` with your username)
- [ ] `python3 publish.py examples/thread.example.json --dry-run` runs without errors

---

## Troubleshooting

**"Missing env vars" error from publish.py**
- Make sure `.env` is in the directory where you run the command
- Or export the variables in your shell

**Figma MCP "permission denied"**
- Re-authorize via browser (official MCP)
- Check PAT hasn't expired (figma-export)

**X API 403 on replies**
- X Free tier restricts programmatic replies (since Feb 2026)
- Upgrade to Basic or Pro tier for thread publishing
- Single tweets still work on Free tier

**Image upload fails**
- Ensure your X app has Read + Write permissions
- Check image file exists and is a valid PNG/JPG
- File size must be under 5MB (images) or 512MB (video)
