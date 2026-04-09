#!/usr/bin/env bash
# ============================================================
# test-local.sh — ทดสอบ poc-company-ai-bot บน local
#
# ใช้: bash scripts/test-local.sh
# ต้องการ: docker compose --profile local-odoo up -d ก่อน
# ============================================================

set -euo pipefail

PASS=0
FAIL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)) || true; }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)) || true; }
skip() { echo -e "  ${YELLOW}~${NC} $1 (skipped)"; ((SKIP++)) || true; }
info() { echo -e "  ${BLUE}→${NC} $1"; }
section() { echo -e "\n${BLUE}══ $1 ══${NC}"; }

# ────────────────────────────────────────────────────────────
# 0. Prerequisites
# ────────────────────────────────────────────────────────────
section "0. Prerequisites"

if ! command -v docker &>/dev/null; then
  fail "docker not found"; exit 1
fi
ok "docker available"

if ! command -v curl &>/dev/null; then
  fail "curl not found"; exit 1
fi
ok "curl available"

OPENCODE_PASSWORD="${OPENCODE_PASSWORD:-changeme}"
OPENCODE_AUTH=$(echo -n "opencode:${OPENCODE_PASSWORD}" | base64)

# ────────────────────────────────────────────────────────────
# 1. Container Health
# ────────────────────────────────────────────────────────────
section "1. Container Health"

check_container() {
  local name=$1 expected_status=$2
  local status
  status=$(docker ps --filter "name=^${name}$" --format "{{.Status}}" 2>/dev/null || echo "")
  if echo "$status" | grep -q "healthy"; then
    ok "${name} — healthy"
  elif echo "$status" | grep -q "Up"; then
    ok "${name} — up (no healthcheck)"
  elif [[ -z "$status" ]]; then
    fail "${name} — not running"
  else
    fail "${name} — ${status}"
  fi
}

check_container "poc-rag-mcp"    "healthy"
check_container "poc-odoo-mcp"   "healthy"
check_container "poc-bot-server" "up"
check_container "poc-odoo-local" "healthy"
check_container "poc-odoo-db"    "healthy"

# ────────────────────────────────────────────────────────────
# 2. Health Endpoints
# ────────────────────────────────────────────────────────────
section "2. Health Endpoints"

check_health() {
  local name=$1 url=$2 expected=$3
  local resp
  resp=$(curl -s --max-time 5 "$url" 2>/dev/null || echo "")
  if echo "$resp" | grep -qi "$expected"; then
    ok "${name} ${url}"
  else
    fail "${name} ${url} — got: ${resp:0:80}"
  fi
}

check_health "rag-mcp"    "http://localhost:5000/health"    "ok"
check_health "odoo-mcp"   "http://localhost:8000/health"    "ok"
check_health "odoo-local" "http://localhost:8069/web/health" "pass"

# ────────────────────────────────────────────────────────────
# 3. RAG MCP Tools
# ────────────────────────────────────────────────────────────
section "3. RAG MCP — company-rag tools"

# MCP initialize → get session
MCP_SESSION=$(curl -si --max-time 10 -X POST http://localhost:5000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  2>/dev/null | grep -i "mcp-session-id:" | awk '{print $2}' | tr -d '\r' || echo "")

if [[ -z "$MCP_SESSION" ]]; then
  fail "RAG MCP — cannot establish session"
else
  ok "RAG MCP session: ${MCP_SESSION:0:12}..."

  # initialized notification
  curl -s --max-time 5 -X POST http://localhost:5000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $MCP_SESSION" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null 2>&1 || true

  # tools/list
  TOOLS=$(curl -sL --max-time 10 -X POST http://localhost:5000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $MCP_SESSION" \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' 2>/dev/null || echo "")

  if echo "$TOOLS" | grep -q "search_company_info"; then
    ok "RAG tools/list — search_company_info, list_knowledge_topics"
  else
    fail "RAG tools/list — tools not found"
  fi

  # list_knowledge_topics
  TOPICS=$(curl -sL --max-time 30 -X POST http://localhost:5000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $MCP_SESSION" \
    -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_knowledge_topics","arguments":{}}}' \
    2>/dev/null || echo "")

  if echo "$TOPICS" | grep -q "isError.*false\|topic\|เกี่ยวกับ\|นโยบาย\|FAQ"; then
    ok "list_knowledge_topics — returned topics"
  elif echo "$TOPICS" | grep -q "isError.*true"; then
    fail "list_knowledge_topics — tool error: $(echo "$TOPICS" | grep -o '"text":"[^"]*"' | head -1)"
  else
    skip "list_knowledge_topics — no data (knowledge not ingested?)"
  fi

  # search_company_info (cold start may take time — 60s timeout)
  info "search_company_info — may take ~60s on cold start (model loading)..."
  SEARCH=$(curl -sL --max-time 90 -X POST http://localhost:5000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $MCP_SESSION" \
    -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_company_info","arguments":{"query":"นโยบายบริษัท"}}}' \
    2>/dev/null || echo "")

  if echo "$SEARCH" | grep -q '"isError":false'; then
    ok "search_company_info — search succeeded"
  elif echo "$SEARCH" | grep -q '"isError":true'; then
    fail "search_company_info — tool error (ChromaDB collection missing? Re-run ingestion)"
  elif [[ -z "$SEARCH" ]]; then
    fail "search_company_info — timeout (model still loading?)"
  else
    skip "search_company_info — unexpected response"
  fi
fi

# ────────────────────────────────────────────────────────────
# 4. Odoo MCP Tools
# ────────────────────────────────────────────────────────────
section "4. Odoo MCP — odoo tools"

ODOO_SESSION=$(curl -si --max-time 10 -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  2>/dev/null | grep -i "mcp-session-id:" | awk '{print $2}' | tr -d '\r' || echo "")

if [[ -z "$ODOO_SESSION" ]]; then
  fail "Odoo MCP — cannot establish session"
else
  ok "Odoo MCP session: ${ODOO_SESSION:0:12}..."

  curl -s --max-time 5 -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $ODOO_SESSION" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null 2>&1 || true

  # tools/list
  ODOO_TOOLS=$(curl -sL --max-time 10 -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $ODOO_SESSION" \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' 2>/dev/null || echo "")

  TOOL_COUNT=$(echo "$ODOO_TOOLS" | grep -o '"name"' | wc -l || echo 0)
  if [[ "$TOOL_COUNT" -ge 5 ]]; then
    ok "Odoo tools/list — ${TOOL_COUNT} tools (search_read, create, write, ...)"
  else
    fail "Odoo tools/list — only ${TOOL_COUNT} tools found"
  fi

  # odoo_version (tests real Odoo connection)
  ODOO_URL="${ODOO_URL:-http://odoo-local:8069}"
  ODOO_DB="${ODOO_DB:-odoo}"
  ODOO_USER="${ODOO_USERNAME:-admin}"
  ODOO_PASS="${ODOO_PASSWORD:-admin}"

  ODOO_VER=$(curl -sL --max-time 15 -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $ODOO_SESSION" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"odoo_version\",\"arguments\":{\"server_url\":\"${ODOO_URL}\",\"db\":\"${ODOO_DB}\",\"username\":\"${ODOO_USER}\",\"password\":\"${ODOO_PASS}\"}}}" \
    2>/dev/null || echo "")

  if echo "$ODOO_VER" | grep -q "server_version"; then
    ODOO_VER_STR=$(echo "$ODOO_VER" | grep -oE 'server_version[^0-9]+[0-9]+\.[0-9]+-[0-9]+' | grep -oE '[0-9]+\.[0-9]+-[0-9]+' || \
      echo "$ODOO_VER" | grep -oE 'server_version[^0-9]+[0-9]+\.[0-9]+' | grep -oE '[0-9]+\.[0-9]+' || echo "?")
    ok "odoo_version — Odoo ${ODOO_VER_STR} (${ODOO_URL})"
  else
    fail "odoo_version — cannot connect to Odoo at ${ODOO_URL}"
  fi
fi

# ────────────────────────────────────────────────────────────
# 5. OpenCode API
# ────────────────────────────────────────────────────────────
section "5. OpenCode API"

OC_RUNNING=$(docker ps --filter "name=^poc-bot-server$" --format "{{.Status}}" 2>/dev/null || echo "")
if [[ -z "$OC_RUNNING" ]]; then
  skip "OpenCode — container not running (start with: docker compose up -d opencode)"
else
  # create session
  OC_SESSION=$(docker exec poc-bot-server wget -qO- \
    --header="Authorization: Basic ${OPENCODE_AUTH}" \
    --header="Content-Type: application/json" \
    --header="x-opencode-directory: %2Fworkspace" \
    --post-data='{"title":"health-check"}' \
    http://0.0.0.0:4096/session 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

  if [[ -z "$OC_SESSION" ]]; then
    fail "OpenCode — cannot create session (auth failed?)"
  else
    ok "OpenCode session: ${OC_SESSION:0:20}..."

    # check MCP connections
    MCP_STATUS=$(docker exec poc-bot-server wget -qO- \
      --header="Authorization: Basic ${OPENCODE_AUTH}" \
      --header="x-opencode-directory: %2Fworkspace" \
      http://0.0.0.0:4096/mcp 2>/dev/null || echo "")

    RAG_STATUS=$(echo "$MCP_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('company-rag',{}).get('status','?'))" 2>/dev/null || echo "?")
    ODOO_STATUS=$(echo "$MCP_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('odoo',{}).get('status','?'))" 2>/dev/null || echo "?")

    if [[ "$RAG_STATUS" == "connected" ]]; then
      ok "OpenCode → company-rag MCP: connected"
    else
      fail "OpenCode → company-rag MCP: ${RAG_STATUS}"
    fi

    if [[ "$ODOO_STATUS" == "connected" ]]; then
      ok "OpenCode → odoo MCP: connected"
    else
      fail "OpenCode → odoo MCP: ${ODOO_STATUS}"
    fi

    # check default model
    DEFAULT_MODEL=$(docker exec poc-bot-server cat /root/.local/state/opencode/model.json 2>/dev/null | \
      python3 -c "import sys,json; r=json.load(sys.stdin).get('recent',[]); print(r[0].get('providerID','')+'/'+r[0].get('modelID','') if r else '?')" 2>/dev/null || echo "?")
    if [[ "$DEFAULT_MODEL" == "opencode/big-pickle" ]]; then
      ok "Default model: ${DEFAULT_MODEL} (free)"
    else
      skip "Default model: ${DEFAULT_MODEL} (expected opencode/big-pickle)"
    fi
  fi
fi

# ────────────────────────────────────────────────────────────
# 6. Knowledge Base
# ────────────────────────────────────────────────────────────
section "6. Knowledge Base"

KNOWLEDGE_DIR="$(cd "$(dirname "$0")/.." && pwd)/knowledge"

check_knowledge() {
  local file=$1
  if [[ ! -f "${KNOWLEDGE_DIR}/${file}" ]]; then
    fail "${file} — not found"
    return
  fi
  local size
  size=$(wc -c < "${KNOWLEDGE_DIR}/${file}")
  if grep -q "\[ชื่อบริษัท\]\|\[รายละเอียด\]\|\[คำถาม" "${KNOWLEDGE_DIR}/${file}" 2>/dev/null; then
    skip "${file} — still has placeholder content (fill in before production)"
  elif [[ "$size" -lt 100 ]]; then
    skip "${file} — very short (${size} bytes), may be incomplete"
  else
    ok "${file} — has content (${size} bytes)"
  fi
}

check_knowledge "about.md"
check_knowledge "products.md"
check_knowledge "faq.md"
check_knowledge "policies.md"

# ────────────────────────────────────────────────────────────
# 7. LINE Bot (optional — needs credentials)
# ────────────────────────────────────────────────────────────
section "7. LINE Bot (optional)"

LINE_RUNNING=$(docker ps --filter "name=^poc-bot-line-bot$" --format "{{.Status}}" 2>/dev/null || echo "")
if [[ -z "$LINE_RUNNING" ]]; then
  skip "LINE bot — not running (ต้องการ LINE_CHANNEL_ACCESS_TOKEN จริง)"
else
  WEBHOOK=$(curl -s --max-time 5 http://localhost:3000/webhook 2>/dev/null || echo "")
  if echo "$WEBHOOK" | grep -qi "method\|bad\|ok\|400\|200"; then
    ok "LINE bot webhook — reachable at :3000"
  else
    skip "LINE bot — running but webhook didn't respond (normal without LINE ping)"
  fi
fi

# ────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}══════════════════════════════════════${NC}"
echo -e " Results: ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}  ${YELLOW}${SKIP} skipped${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}"

if [[ "$FAIL" -gt 0 ]]; then
  echo ""
  echo "Tips สำหรับ failures:"
  echo "  • Container ไม่ start  → docker compose --profile local-odoo up -d --build"
  echo "  • ChromaDB error       → docker compose run --rm rag-ingestion && docker compose restart rag-mcp"
  echo "  • Odoo connection fail → ตรวจ ODOO_URL/ODOO_DB/ODOO_USERNAME/ODOO_PASSWORD ใน .env"
  echo "  • OpenCode auth fail   → ตรวจ OPENCODE_PASSWORD ใน .env"
  exit 1
fi

echo ""
echo "พร้อมส่งให้ทีมทดสอบ! 🎉"
exit 0
