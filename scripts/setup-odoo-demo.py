#!/usr/bin/env python3
"""
setup-odoo-demo.py — ติดตั้ง Odoo modules + สร้าง demo data สำหรับทดสอบ ingestion

ใช้: python3 scripts/setup-odoo-demo.py
ต้องการ: poc-odoo-local กำลังรันอยู่ (docker compose --profile local-odoo up -d)

สิ่งที่ script นี้ทำ:
  1. Install module: sale (รวม product, uom ฯลฯ)
  2. สร้าง product categories
  3. สร้าง demo products (สินค้า/บริการ ภาษาไทย)
  4. ตรวจสอบว่า ingestion จะดึงได้
"""

import sys
import time
import xmlrpc.client

# ─────────────────────────────────────────────
# Config (ตรงกับ .env local defaults)
# ─────────────────────────────────────────────
URL      = "http://localhost:8069"
DB       = "odoo"
USERNAME = "admin"
PASSWORD = "admin"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def connect():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("✗ Authentication failed — ตรวจสอบ ODOO credentials")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    return uid, models

def rpc(models, uid, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})

def ok(msg):  print(f"  ✓ {msg}")
def info(msg): print(f"  → {msg}")
def fail(msg): print(f"  ✗ {msg}")

# ─────────────────────────────────────────────
# 1. Install modules
# ─────────────────────────────────────────────
def install_modules(models, uid, module_names: list[str]):
    print("\n══ Install Modules ══")
    for name in module_names:
        ids = rpc(models, uid, "ir.module.module", "search", [[["name", "=", name]]])
        if not ids:
            fail(f"module '{name}' not found")
            continue
        [mod] = rpc(models, uid, "ir.module.module", "read", [ids], {"fields": ["name", "state"]})
        if mod["state"] == "installed":
            ok(f"{name} — already installed")
            continue
        info(f"installing {name} ...")
        rpc(models, uid, "ir.module.module", "button_immediate_install", [ids])
        # wait for install (server may restart internally)
        for attempt in range(30):
            time.sleep(3)
            try:
                [status] = rpc(models, uid, "ir.module.module", "read", [ids], {"fields": ["state"]})
                if status["state"] == "installed":
                    ok(f"{name} — installed")
                    break
            except Exception:
                # reconnect after server restart
                uid, models = connect()
        else:
            fail(f"{name} — install timeout")
    return uid, models

# ─────────────────────────────────────────────
# 2. Create product categories
# ─────────────────────────────────────────────
CATEGORIES = [
    "ซอฟต์แวร์และบริการ IT",
    "ฝึกอบรมและที่ปรึกษา",
    "ฮาร์ดแวร์และอุปกรณ์",
]

def setup_categories(models, uid) -> dict[str, int]:
    print("\n══ Product Categories ══")
    categ_ids = {}
    for name in CATEGORIES:
        existing = rpc(models, uid, "product.category", "search", [[["name", "=", name]]])
        if existing:
            categ_ids[name] = existing[0]
            ok(f"{name} — exists")
        else:
            new_id = rpc(models, uid, "product.category", "create", [{"name": name}])
            categ_ids[name] = new_id
            ok(f"{name} — created (id={new_id})")
    return categ_ids

# ─────────────────────────────────────────────
# 3. Demo products
# ─────────────────────────────────────────────
def make_products(categ_ids: dict[str, int]) -> list[dict]:
    sw  = categ_ids.get("ซอฟต์แวร์และบริการ IT", False)
    trn = categ_ids.get("ฝึกอบรมและที่ปรึกษา", False)
    hw  = categ_ids.get("ฮาร์ดแวร์และอุปกรณ์", False)

    return [
        # ─── Software / SaaS ───
        {
            "name": "ระบบ ERP Odoo Cloud (รายปี)",
            "description_sale": (
                "ระบบบริหารธุรกิจครบวงจร Odoo 19 บน Cloud\n"
                "- จัดการบัญชี, คลังสินค้า, การขาย, HR ในระบบเดียว\n"
                "- รองรับภาษาไทย, VAT 7%, ใบกำกับภาษีอิเล็กทรอนิกส์\n"
                "- Support ภาษาไทยตลอด 24 ชม.\n"
                "- ราคารวม Implementation และ Training เบื้องต้น"
            ),
            "list_price": 120_000.0,
            "categ_id": sw,
            "sale_ok": True,
            "type": "service",
        },
        {
            "name": "ระบบ POS (Point of Sale)",
            "description_sale": (
                "ระบบขายหน้าร้านเชื่อมต่อ Odoo\n"
                "- รองรับ Barcode, Touch Screen, Printer ใบเสร็จ\n"
                "- ออฟไลน์ได้ — sync อัตโนมัติเมื่อมีสัญญาณ\n"
                "- รายงาน Real-time ผ่านมือถือ"
            ),
            "list_price": 45_000.0,
            "categ_id": sw,
            "sale_ok": True,
            "type": "service",
        },
        {
            "name": "แพ็กเกจ HR & Payroll",
            "description_sale": (
                "โมดูล HR และเงินเดือนสำหรับ Odoo\n"
                "- คำนวณเงินเดือน ภาษี ประกันสังคม อัตโนมัติ\n"
                "- ระบบลา, โอที, สลิปเงินเดือนออนไลน์\n"
                "- Export ไฟล์นำส่งประกันสังคม/กรมสรรพากร"
            ),
            "list_price": 35_000.0,
            "categ_id": sw,
            "sale_ok": True,
            "type": "service",
        },
        # ─── Training / Consulting ───
        {
            "name": "อบรม Odoo สำหรับผู้ใช้งาน (2 วัน)",
            "description_sale": (
                "หลักสูตรอบรมการใช้งาน Odoo สำหรับ End User\n"
                "- เนื้อหาครอบคลุม: การขาย, ใบแจ้งหนี้, รายงาน\n"
                "- Workshop ฝึกปฏิบัติจริงบน Demo Database\n"
                "- เอกสารประกอบการอบรมภาษาไทย\n"
                "- รองรับกลุ่ม 8-15 คน"
            ),
            "list_price": 25_000.0,
            "categ_id": trn,
            "sale_ok": True,
            "type": "service",
        },
        {
            "name": "บริการที่ปรึกษา Odoo (รายวัน)",
            "description_sale": (
                "บริการที่ปรึกษาด้านระบบ Odoo โดยผู้เชี่ยวชาญ\n"
                "- วิเคราะห์ process และออกแบบระบบให้เหมาะกับธุรกิจ\n"
                "- ให้คำแนะนำ best practice การใช้ Odoo\n"
                "- On-site หรือ Remote\n"
                "- ราคาต่อวัน (7 ชม.)"
            ),
            "list_price": 15_000.0,
            "categ_id": trn,
            "sale_ok": True,
            "type": "service",
        },
        {
            "name": "Customization Odoo (ต่อ Module)",
            "description_sale": (
                "พัฒนาโมดูล Odoo ตามความต้องการเฉพาะของธุรกิจ\n"
                "- รับพัฒนา custom module, report, dashboard\n"
                "- Python + OWL framework\n"
                "- มี Unit Test และเอกสาร Technical Spec\n"
                "- Warranty 3 เดือนหลังส่งมอบ"
            ),
            "list_price": 50_000.0,
            "categ_id": trn,
            "sale_ok": True,
            "type": "service",
        },
        # ─── Hardware ───
        {
            "name": "เครื่อง POS Terminal (All-in-One)",
            "description_sale": (
                "เครื่อง POS สำหรับร้านค้าปลีก/ร้านอาหาร\n"
                "- หน้าจอสัมผัส 15 นิ้ว + Barcode Scanner ในตัว\n"
                "- พร้อม Thermal Printer 80mm\n"
                "- RAM 8GB, SSD 256GB, Windows 11\n"
                "- ติดตั้ง Odoo POS พร้อมใช้งาน"
            ),
            "list_price": 28_000.0,
            "categ_id": hw,
            "sale_ok": True,
            "type": "consu",
        },
        {
            "name": "Barcode Scanner (USB + Bluetooth)",
            "description_sale": (
                "เครื่องอ่าน Barcode 2-in-1 รองรับ 1D/2D/QR Code\n"
                "- เชื่อมต่อ USB และ Bluetooth 5.0\n"
                "- ระยะอ่าน 0-50 cm\n"
                "- รองรับการทำงานกับ Odoo POS และ Inventory"
            ),
            "list_price": 3_500.0,
            "categ_id": hw,
            "sale_ok": True,
            "type": "consu",
        },
    ]


def create_products(models, uid, categ_ids: dict[str, int]):
    print("\n══ Demo Products ══")
    products = make_products(categ_ids)
    created = 0
    for p in products:
        existing = rpc(models, uid, "product.template", "search",
                       [[["name", "=", p["name"]]]])
        if existing:
            ok(f"{p['name'][:50]} — exists")
        else:
            new_id = rpc(models, uid, "product.template", "create", [p])
            ok(f"{p['name'][:50]} — created (id={new_id}, ฿{p['list_price']:,.0f})")
            created += 1
    info(f"สร้างใหม่ {created} / {len(products)} products")

# ─────────────────────────────────────────────
# 4. Verify — what ingestion will see
# ─────────────────────────────────────────────
def verify(models, uid):
    print("\n══ Verify (what rag-ingestion will see) ══")
    records = rpc(models, uid, "product.template", "search_read",
                  [[["sale_ok", "=", True]]],
                  {"fields": ["name", "list_price", "categ_id"], "limit": 20})
    if records:
        ok(f"{len(records)} products พร้อม ingest")
        for r in records:
            categ = r["categ_id"][1] if r.get("categ_id") else "-"
            print(f"    • {r['name'][:45]:<45}  ฿{r['list_price']:>10,.0f}  [{categ}]")
    else:
        fail("ไม่พบ product ที่ sale_ok=True")

# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
def main():
    print("═" * 50)
    print(" Odoo Demo Data Setup")
    print(f" {URL}  db={DB}")
    print("═" * 50)

    uid, models = connect()
    ok(f"authenticated (uid={uid})")

    uid, models = install_modules(models, uid, ["sale"])
    categ_ids   = setup_categories(models, uid)
    create_products(models, uid, categ_ids)
    verify(models, uid)

    print("\n══ Next Step ══")
    print("  INGEST_SOURCE=all docker compose run --rm rag-ingestion")
    print("  docker compose restart rag-mcp")
    print("═" * 50)


if __name__ == "__main__":
    main()
