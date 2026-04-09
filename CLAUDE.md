# CLAUDE.md

ไฟล์นี้ให้ context กับ AI tools (Claude Code, OpenCode ฯลฯ) เมื่อทำงานใน repo นี้

## Project Overview

LINE OA AI Bot template สำหรับตอบข้อมูลบริษัทผ่าน RAG + Odoo MCP
**1 repo = 1 บริษัท** — clone แล้วแก้ค่าตามบริษัทนั้นๆ
Default AI model: **`opencode/big-pickle`** (ฟรี ไม่ต้องใช้ API key)

## โครงสร้างหลัก

```
bot-service/         LINE bot (Bun) + OpenCode AI engine
company-rag/
  ingestion/         ETL pipeline: markdown + Odoo → ChromaDB + BM25
  mcp-server/        FastMCP streamable-http server, port 5000
odoo-mcp/            git submodule: odoo-mcp-claude, port 8000 (streamable-http)
knowledge/           .md files ข้อมูลบริษัท — แก้ที่นี่เพื่อเปลี่ยนเนื้อหา
workspace/
  AGENTS.md          system prompt + tool routing rules — แก้ชื่อบริษัทที่นี่
  opencode.jsonc     MCP config (ชี้ไป rag-mcp + odoo-mcp)
docker-compose.yml   orchestrate ทุก services
.env.example         template credentials
```

## Services และ Ports

| Service | Port | Transport |
|---------|------|-----------|
| line-bot | 3000 | HTTP |
| opencode | 4096 | HTTP REST (Basic auth) |
| rag-mcp | 5000 | MCP streamable-http + `/health` |
| odoo-mcp | 8000 | MCP streamable-http + `/health` |
| odoo-local *(profile)* | 8069 | HTTP (local test only) |
| odoo-db *(profile)* | — | PostgreSQL internal |

## First-Run Flow

```
docker compose --profile local-odoo up -d
  └─ rag-ingestion (one-shot: ingest knowledge/*.md → ChromaDB + BM25)
  └─ odoo-init (one-shot: init Odoo DB schema)
  └─ rag-mcp, odoo-mcp, opencode, line-bot (start after dependencies healthy)
```

## การ Ingest ข้อมูล

```bash
# default — ingest เฉพาะ markdown (ไม่ต้อง Odoo credentials)
docker compose run --rm rag-ingestion

# ingest ทั้งหมด (markdown + Odoo sync — ต้องตั้ง INGEST_SOURCE=all ใน .env)
INGEST_SOURCE=all docker compose run --rm rag-ingestion

# ingest เฉพาะ Odoo
docker compose run --rm rag-ingestion ingest --source odoo
```

## Tool Routing Logic

อยู่ใน `workspace/AGENTS.md` — LLM อ่านแล้วตัดสินใจเองว่าจะใช้ tool ไหน:
- `search_company_info` → ข้อมูล static (RAG) เช่น นโยบาย FAQ บริการ
- `odoo_search_read` → ข้อมูล realtime (Odoo) เช่น สต็อก ราคา ออเดอร์
- ทั้งคู่ → คำถามที่ต้องการทั้ง description + live data

## สิ่งที่ต้องแก้เมื่อใช้กับบริษัทใหม่

1. `.env` — credentials (LINE, Odoo, Cloudflare)
2. `workspace/AGENTS.md` — แทนที่ `[ชื่อบริษัท]`
3. `knowledge/*.md` — ข้อมูลบริษัทจริง

## สิ่งที่ไม่ควรแก้โดยไม่จำเป็น

- `company-rag/ingestion/src/embedder.py` — embedding model และ chunking logic
- `company-rag/mcp-server/src/retriever.py` — hybrid search + RRF + rerank
- `bot-service/src/index.ts` — LINE webhook และ OpenCode client

## Odoo submodule

`odoo-mcp/` เป็น git submodule ชี้ไป `monthop-gmail/odoo-mcp-claude`
ใช้ **streamable HTTP** transport (port 8000) — ไม่ใช่ stdio

```bash
# อัปเดต submodule เป็น version ล่าสุด
git submodule update --remote odoo-mcp
```

## Common Commands

```bash
# รัน local (Local Odoo + ทุก service)
docker compose --profile local-odoo up -d --build

# รัน production (ใช้ Odoo Cloud — ตั้ง ODOO_URL ใน .env ก่อน)
docker compose up -d --build

# ดู logs
docker compose logs -f [service]

# rebuild เฉพาะ service
docker compose up -d --build rag-mcp

# check health
curl http://localhost:5000/health   # rag-mcp
curl http://localhost:8000/health   # odoo-mcp
curl http://localhost:8069/web/health  # local odoo (profile เท่านั้น)

# ดู default model ที่ใช้
docker exec poc-bot-server cat /root/.local/state/opencode/model.json
```

## Local → Cloud Switch

เปลี่ยนจาก local Odoo เป็น Odoo Cloud แค่แก้ `.env` 3 บรรทัด:
```env
ODOO_URL=https://yourcompany.odoo.com
ODOO_DB=your_database
ODOO_PASSWORD=your_api_key   # Settings → Technical → API Keys
```
แล้ว `docker compose up -d --no-deps odoo-mcp`

## Known Limitations

- RAG model download หนัก ~650MB (multilingual-e5-base + reranker) — cold start ช้าครั้งแรก
- Model cache ไม่ persistent ข้าม container restart (re-download ทุกครั้ง)
- OpenCode `serve` ไม่ใช่ production-grade API server — เหมาะสำหรับ traffic ปานกลาง
- Default LLM: `opencode/big-pickle` (ฟรี) — เปลี่ยนได้ด้วย `/model` command ใน LINE
