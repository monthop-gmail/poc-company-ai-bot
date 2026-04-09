# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

poc-company-ai-bot — bridges LINE Messaging API to Claude AI via OpenCode server as middleware. Three Docker services: LINE bot (Bun), OpenCode server (Alpine, includes odoo-mcp), Cloudflare tunnel.

## Commands

```bash
# Local development
cp .env.example .env   # Set credentials first
bun install
bun dev                # Run bot locally

# Docker deployment (production)
docker compose up -d --build            # Build and deploy all services
docker compose up -d --build line-bot   # Rebuild only LINE bot
docker compose up -d --build opencode   # Rebuild only OpenCode server

# Logs
docker logs poc-bot-line-bot --tail 30    # LINE bot logs
docker logs poc-bot-server --tail 30      # OpenCode server logs
docker logs poc-bot-tunnel                # Tunnel logs

# Useful checks
docker exec poc-bot-server cat /root/.local/state/opencode/model.json   # Check default model
docker exec poc-bot-server cat /root/.config/opencode/opencode.json     # Check Claude provider config
```

## Architecture

```
LINE app → Cloudflare Tunnel → line-bot (Bun, port 3000) → OpenCode (port 4096) → AI Model
                                                                  ↕
                                                            odoo-mcp (stdio)
```

- **`src/index.ts`** — Single-file application. All bot logic: webhook handler, session management, OpenCode REST client, LINE message sending, image handling, group chat filtering, user memory, time context, LINE commands, web /about page.
- **`opencode.json`** — Anthropic + DeepSeek + Google + Qwen provider configuration for OpenCode (mounted read-only into container)
- **`Dockerfile`** — LINE bot container (`oven/bun:1`, Debian)
- **`Dockerfile.opencode`** — OpenCode server extending `ghcr.io/anomalyco/opencode:latest` (Alpine) with dev tools, odoo-mcp, and pre-configured model.json for Claude
- **`docker-compose.yml`** — Orchestrates 3 services with 2 named volumes + config mount
- **`workspace/AGENTS.md`** — Instructions file for Claude inside the container

## Key Design Decisions

**OpenCode REST API (not SDK):** All calls use direct `fetch()` to `http://opencode:4096` with Basic auth (`opencode:{password}`) and `x-opencode-directory` header.

**Model switching via `/model` command:** Users can switch models per session. Default: `opencode/big-pickle` (free via OpenCode Zen). Model preference stored in `modelPrefs` Map per group/user.

**MCP Tools:** `workspace/opencode.jsonc` configures MCP servers. Currently: `odoo-mcp-tarad` (Odoo ERP via XML-RPC, stdio transport).

**Question tool prevention:** Every prompt is prefixed with `[IMPORTANT: Do NOT use the question tool...]` because the question tool blocks the REST API indefinitely waiting for interactive input.

**Reply strategy:** Always use `replyMessage` first (free, unlimited) before falling back to `pushMessage` (300/month on free plan).

## Environment Variables

Required in `.env` (not committed):
- `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET` — LINE Messaging API credentials
- `ANTHROPIC_API_KEY` — Anthropic API key
- `DEEPSEEK_API_KEY` — DeepSeek API key (optional)
- `GROQ_API_KEY` — Groq API key (optional, for Llama/Mixtral/Gemma models)
- `GOOGLE_API_KEY` — Google AI API key (optional)
- `QWEN_API_KEY` — Qwen/DashScope API key (optional)
- `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` — Odoo ERP credentials for odoo-mcp
- `CLOUDFLARE_TUNNEL_TOKEN` — Tunnel authentication
- `OPENCODE_PASSWORD` — OpenCode server Basic auth password (default: `changeme`)
- `GITHUB_TOKEN` — GitHub PAT for `gh` CLI inside OpenCode container (optional)
- `LINE_OA_URL` — LINE Official Account URL
- `PROMPT_TIMEOUT_MS` — Prompt timeout in ms (default: `120000`)

## Docker Volumes

- **`poc-bot-data`** → `/root/.local/share/opencode` — auth.json (provider tokens)
- **`poc-bot-state`** → `/root/.local/state/opencode` — model.json (default model)

## Webhook URL

`https://sumana.online/webhook`

## GitHub

- Repo: `monthop-gmail/poc-company-ai-bot`
- Workspace: `monthop-gmail/poc-company-ai-bot-workspace`
