# poc-company-ai-bot

LINE OA AI Bot สำหรับตอบข้อมูลบริษัท — ใช้ RAG + Odoo realtime

**1 repo clone = 1 บริษัท**

## Architecture

```
LINE User
    ↓
LINE OA → bot-service (Bun + OpenCode)
              ↓                ↓
        company-rag-mcp    odoo-mcp
        (static knowledge) (Odoo Cloud realtime)
              ↓                ↓
         ChromaDB+BM25     XML-RPC → Odoo Cloud
```

---

## Setup ใหม่สำหรับบริษัท

### 1. Clone repo
```bash
git clone https://github.com/monthop-gmail/poc-company-ai-bot <ชื่อบริษัท>-bot
cd <ชื่อบริษัท>-bot
```

### 2. ไฟล์ที่ต้องแก้ (checklist)

```
✅ .env                        ← credentials ทั้งหมด
✅ workspace/AGENTS.md         ← ชื่อบริษัท + บุคลิก bot
✅ knowledge/about.md          ← ข้อมูลบริษัท
✅ knowledge/products.md       ← สินค้า/บริการ
✅ knowledge/faq.md            ← คำถามที่พบบ่อย
✅ knowledge/policies.md       ← นโยบายต่างๆ
```

### 3. ตั้งค่า .env
```bash
cp .env.example .env
```

แก้ค่าใน `.env`:
```env
# LINE OA (จาก LINE Developers Console)
LINE_CHANNEL_ACCESS_TOKEN=
LINE_CHANNEL_SECRET=
LINE_OA_URL=

# Odoo Cloud
ODOO_URL=https://yourcompany.odoo.com
ODOO_DB=yourdb
ODOO_USERNAME=admin
ODOO_PASSWORD=your_api_key     # Settings → Technical → API Keys

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=
```

> API keys อื่น (ANTHROPIC_API_KEY ฯลฯ) ไม่บังคับ — default model ฟรีผ่าน OpenCode Zen

### 4. ใส่ข้อมูลบริษัทใน knowledge/
แก้ไฟล์ `knowledge/*.md` ให้ตรงกับบริษัท

### 5. แก้ workspace/AGENTS.md
เปลี่ยน `[ชื่อบริษัท]` เป็นชื่อจริง และปรับบุคลิก bot ตามต้องการ

### 6. รัน
```bash
docker compose up -d --build
```

ระบบจะ:
1. Ingest `knowledge/*.md` + sync ข้อมูลจาก Odoo → ChromaDB
2. Start rag-mcp + odoo-mcp
3. Start OpenCode + LINE bot

---

## โครงสร้าง Repo

```
.
├── bot-service/          LINE bot (Bun) + OpenCode engine
│   ├── src/index.ts      webhook, session, commands
│   ├── Dockerfile
│   └── Dockerfile.opencode
├── company-rag/
│   ├── ingestion/        ETL: markdown + Odoo → ChromaDB + BM25
│   └── mcp-server/       FastMCP HTTP server (port 5000)
├── odoo-mcp/             git submodule → odoo-mcp-claude (port 8000)
├── knowledge/            ใส่ .md ข้อมูลบริษัทที่นี่
├── workspace/
│   ├── AGENTS.md         system prompt + tool routing rules
│   └── opencode.jsonc    MCP config
├── docker-compose.yml    orchestrate ทุก services
└── .env.example
```

---

## Services

| Service | Port | หน้าที่ |
|---------|------|---------|
| line-bot | 3000 | LINE webhook |
| opencode | 4096 | AI engine (OpenCode) |
| rag-mcp | 5000 | RAG search MCP server |
| odoo-mcp | 8000 | Odoo MCP server |
| cloudflared | — | Cloudflare tunnel |
| **odoo-local** *(profile)* | **8069** | **Local Odoo 19 สำหรับทดสอบ** |
| odoo-db *(profile)* | — | PostgreSQL 15 (ใช้กับ odoo-local) |

---

## Local Odoo (สำหรับทดสอบ)

ใช้สำหรับทีมที่ยังไม่มี Odoo Cloud หรือต้องการทดสอบ flow ครบก่อน deploy จริง

### เปิด Local Odoo

```bash
docker compose --profile local-odoo up -d
```

### ตั้งค่าครั้งแรก

1. เปิด browser: **http://localhost:8069**
2. สร้าง database:
   - Database Name: `odoo`
   - Email: `admin@example.com`
   - Password: `admin`
   - Language: Thai (ถ้ามี)
3. แก้ `.env`:
   ```env
   ODOO_URL=http://odoo-local:8069
   ODOO_DB=odoo
   ODOO_USERNAME=admin
   ODOO_PASSWORD=admin
   ```
4. Restart odoo-mcp:
   ```bash
   docker compose up -d --no-deps odoo-mcp
   ```

### ทดสอบ connection

```bash
# health ของ odoo-mcp (ชี้ไป local odoo แล้ว)
curl http://localhost:8000/health

# ทดสอบ MCP tool โดยตรง
curl -sL -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### หยุด Local Odoo

```bash
docker compose --profile local-odoo down
# ถ้าต้องการลบข้อมูลด้วย:
docker compose --profile local-odoo down -v
```

---

## LINE Bot Commands

| Command | หน้าที่ |
|---------|---------|
| `/new` | เริ่ม session ใหม่ |
| `/model` | เปลี่ยน AI model |
| `/help` | ดูคำสั่งทั้งหมด |

---

## Tool Routing

Bot ตัดสินใจเองว่าจะใช้ tool ไหน ตาม rules ใน `workspace/AGENTS.md`:

| คำถาม | Tool |
|-------|------|
| นโยบาย, FAQ, รายละเอียดสินค้า | RAG (`search_company_info`) |
| สต็อก, ราคา, ออเดอร์, สาขา | Odoo live (`odoo_search_read`) |
| ต้องการทั้งสอง | ใช้ทั้งคู่แล้วรวมคำตอบ |

---

## อัปเดต Knowledge Base

เมื่อแก้ไข `knowledge/*.md` ให้ re-ingest:
```bash
docker compose run --rm rag-ingestion ingest --source markdown
```

Sync ข้อมูลจาก Odoo ใหม่:
```bash
docker compose run --rm rag-ingestion ingest --source odoo
```

---

## Logs

```bash
docker compose logs -f line-bot      # LINE bot
docker compose logs -f opencode      # OpenCode engine
docker compose logs -f rag-mcp       # RAG server
docker compose logs -f odoo-mcp      # Odoo MCP
```

---

## RAG: เทียบกับ legal-th-suite (ต้นแบบ)

RAG ใน repo นี้ดัดแปลงมาจาก [legal-th-suite](https://github.com/monthop-gmail/legal-th-suite)

### สิ่งที่เหมือนกัน (core pipeline)

| ส่วน | ทั้งสอง |
|------|---------|
| Embedding | `intfloat/multilingual-e5-base` + prefix "passage:"/"query:" |
| Vector DB | ChromaDB persistent |
| Keyword | BM25 + pythainlp tokenizer |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Model loading | Lazy singleton (โหลดครั้งเดียว) |

### สิ่งที่เปลี่ยน

| ส่วน | legal-th-suite | company-rag |
|------|---------------|-------------|
| Chunking | 1 มาตรา = 1 chunk (Thai law regex) | 1 heading = 1 chunk (markdown split) |
| Data source | ตัวบทกฎหมายไทย | Markdown files + Odoo Cloud |
| MCP transport | stdio | streamable-http (Docker-friendly) |
| MCP tools | 3 (statute lookup, search, glossary) | 2 (search, list_topics) |
| Re-index | Upsert incremental | Delete + recreate (simpler) |
| Topic filter | มี | มี (`topic_filter` param ใน `search_company_info`) |
| Metadata | law_id, section_number, elements, cross_refs | source, source_type, heading, topic |

### Roadmap (ปรับปรุงที่ยังค้างอยู่)

- [ ] Configurable ChromaDB HTTP client (รองรับ remote vector DB)
- [ ] Upsert incremental แทน full re-index (ประหยัดเวลา sync)
- [ ] Direct lookup tool `get_company_doc(id)` สำหรับดึงเอกสารตาม ID โดยตรง

---

## Note: CPU-only PyTorch

`company-rag` ใช้ `sentence-transformers` ซึ่งต้องการ PyTorch

**ทำไมถึงใช้ CPU-only:**

```
# requirements.txt ทั้ง ingestion และ mcp-server
--extra-index-url https://download.pytorch.org/whl/cpu
torch
```

| | CUDA (default) | CPU-only (เราใช้) |
|--|---------------|-----------------|
| Download | ~2.5GB | ~250MB |
| Image size | ~3GB+ | ~700MB |
| Build time | 15-20 นาที | 3-5 นาที |
| ต้องการ GPU | ✅ | ❌ |
| เหมาะกับ | GPU server | **server ทั่วไป** ✅ |

**Performance บน CPU:** model `multilingual-e5-base` (~278M params) ใช้ CPU ได้สบาย latency ~100-300ms ต่อ query — เพียงพอสำหรับ LINE bot ปกติ

**ถ้ามี GPU:** ลบ `--extra-index-url` และ `torch` ออก ให้ `sentence-transformers` ดึง dependency เองตามปกติ

---

## Note: RAG ทำงานเมื่อไหร่

`sentence-transformers` (embedding + reranking) ถูกใช้ **2 ที่**:

### 1. Ingestion — รันครั้งเดียว
```
knowledge/*.md + Odoo data → embed ทุก chunk → ChromaDB
```
รันตอน setup หรือเมื่ออัปเดต knowledge base เท่านั้น

### 2. MCP server — ทุกครั้งที่ user ถาม
```
user ถาม → embed query → ค้น ChromaDB → BM25 → RRF → rerank → ส่งให้ LLM
```

**ไม่ช้า เพราะ lazy singleton** — model โหลดครั้งแรกครั้งเดียว แล้ว cache ตลอด container

| | cold start (ครั้งแรก) | ครั้งถัดไป |
|--|----------------------|-----------|
| Load model | ~5-10 วินาที | ข้ามไป |
| Embed query | ~100-300ms | ~100-300ms |
| Rerank | ~50-100ms | ~50-100ms |
| **รวม** | **~10 วินาที** | **~200-400ms** |
