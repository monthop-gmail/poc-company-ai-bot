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
