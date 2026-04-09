# CLAUDE.md

ไฟล์นี้ให้ context กับ AI tools (Claude Code, OpenCode ฯลฯ) เมื่อทำงานใน repo นี้

## Project Overview

LINE OA AI Bot template สำหรับตอบข้อมูลบริษัทผ่าน RAG + Odoo MCP
**1 repo = 1 บริษัท** — clone แล้วแก้ค่าตามบริษัทนั้นๆ

## โครงสร้างหลัก

```
bot-service/         LINE bot (Bun) + OpenCode AI engine
company-rag/
  ingestion/         ETL pipeline: markdown + Odoo → ChromaDB + BM25
  mcp-server/        FastMCP HTTP server, port 5000
odoo-mcp/            git submodule: odoo-mcp-claude, port 8000
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
| opencode | 4096 | HTTP REST |
| rag-mcp | 5000 | MCP streamable-http |
| rag health | 5001 | HTTP (background thread) |
| odoo-mcp | 8000 | MCP streamable-http |

## การ Ingest ข้อมูล

```bash
# ingest ทั้งหมด (markdown + Odoo)
docker compose run --rm rag-ingestion ingest --source all

# ingest เฉพาะ markdown
docker compose run --rm rag-ingestion ingest --source markdown

# ingest เฉพาะ Odoo
docker compose run --rm rag-ingestion ingest --source odoo
```

## Tool Routing Logic

อยู่ใน `workspace/AGENTS.md` — LLM อ่านแล้วตัดสินใจเองว่าจะใช้ tool ไหน:
- `search_company_info` → ข้อมูล static (RAG)
- `odoo_search_read` → ข้อมูล realtime (Odoo Cloud)
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

```bash
# อัปเดต submodule เป็น version ล่าสุด
git submodule update --remote odoo-mcp
```

## Common Commands

```bash
# รัน / rebuild
docker compose up -d --build

# ดู logs
docker compose logs -f [service]

# rebuild เฉพาะ service
docker compose up -d --build rag-mcp

# check health
curl http://localhost:5001/health   # rag-mcp
curl http://localhost:8000/health   # odoo-mcp
```

## Known Limitations

- RAG model download หนัก ~650MB (multilingual-e5-base + reranker) — cold start ช้า
- OpenCode `serve` ไม่ใช่ production-grade API server — เหมาะสำหรับ traffic ปานกลาง
- Default LLM: `opencode/big-pickle` (ฟรี) — เปลี่ยนได้ด้วย `/model` command ใน LINE
