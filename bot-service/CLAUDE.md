# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

poc-company-ai-bot — LINE OA AI Bot ที่ใช้ RAG + Odoo MCP ตอบข้อมูลบริษัท
ส่วน `bot-service/` มี 2 containers: LINE bot (Bun) + OpenCode AI engine

## Architecture

```
LINE app → Cloudflare Tunnel → line-bot (Bun, port 3000) → OpenCode (port 4096) → AI Model
                                                                  ↕               ↕
                                                          company-rag MCP    odoo MCP
                                                          (streamable-http)  (streamable-http)
                                                          port 5000          port 8000
```

## Files

- **`src/index.ts`** — Single-file application. All bot logic: webhook handler, session management, OpenCode REST client, LINE message sending, image handling, group chat filtering, user memory, time context, LINE commands.
- **`opencode.json`** — Provider config (mounted read-only). Paid providers commented out — default uses OpenCode Zen free models.
- **`Dockerfile`** — LINE bot container (`oven/bun:1`, Debian)
- **`Dockerfile.opencode`** — OpenCode server (`ghcr.io/anomalyco/opencode:latest`, Alpine). Pre-configures `big-pickle` as default model. Installs git, curl, jq, gh, node, npm, python3.

## Commands

```bash
# Local development (bot only)
bun install
bun dev

# Docker (full stack — run from repo root)
docker compose --profile local-odoo up -d --build   # local Odoo
docker compose up -d --build                         # production (Odoo Cloud)

# Logs
docker logs poc-bot-line-bot --tail 30
docker logs poc-bot-server --tail 30

# Check default model
docker exec poc-bot-server cat /root/.local/state/opencode/model.json
```

## Key Design Decisions

**OpenCode REST API (not SDK):** All calls use direct `fetch()` to `http://opencode:4096` with Basic auth (`opencode:{password}`) and `x-opencode-directory` header pointing to `/workspace`.

**Default model:** `opencode/big-pickle` (free via OpenCode Zen — no API key needed). Baked into image via `Dockerfile.opencode`. Users can switch per-session with `/model` command.

**MCP Tools:** `workspace/opencode.jsonc` configures 2 remote MCP servers over streamable HTTP:
- `company-rag` → `http://rag-mcp:5000/mcp` (RAG: `search_company_info`, `list_knowledge_topics`)
- `odoo` → `http://odoo-mcp:8000/mcp` (Odoo: `odoo_search_read`, `odoo_create`, etc.)

**Question tool prevention:** Every prompt is prefixed with `[IMPORTANT: Do NOT use the question tool...]` because the question tool blocks the REST API indefinitely.

**Reply strategy:** Always use `replyMessage` first (free, unlimited) before falling back to `pushMessage` (300/month free plan).

**Group chat:** Bot responds `[SKIP]` when message is clearly not directed at it. Handled via AGENTS.md instruction.

## Environment Variables

```
LINE_CHANNEL_ACCESS_TOKEN  — LINE Messaging API
LINE_CHANNEL_SECRET        — LINE Messaging API
LINE_OA_URL                — LINE Official Account URL (optional)
OPENCODE_PASSWORD          — Basic auth password (default: changeme)
PROMPT_TIMEOUT_MS          — Prompt timeout ms (default: 120000)
ODOO_URL/DB/USERNAME/PASSWORD — passed to odoo-mcp container (not used directly here)

# Paid AI providers — all optional, leave empty to use free OpenCode Zen models
ANTHROPIC_API_KEY
DEEPSEEK_API_KEY / GOOGLE_API_KEY / QWEN_API_KEY / GROQ_API_KEY
```

## Docker Volumes

- **`poc-bot-data`** → `/root/.local/share/opencode` — provider auth tokens
- **`poc-bot-state`** → `/root/.local/state/opencode` — model.json (default model preference)
