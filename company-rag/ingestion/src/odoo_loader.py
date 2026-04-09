"""
Odoo Loader: ดึงข้อมูลจาก Odoo Cloud ผ่าน XML-RPC แล้วแปลงเป็น DocumentChunk
"""

from __future__ import annotations

import logging
import os
import xmlrpc.client
from dataclasses import dataclass

from .parser import DocumentChunk

logger = logging.getLogger(__name__)


class OdooLoader:
    def __init__(
        self,
        url: str,
        db: str,
        username: str,
        password: str,
    ):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self._uid: int | None = None
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _authenticate(self) -> int:
        if self._uid is None:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self._uid = common.authenticate(self.db, self.username, self.password, {})
            logger.info("Odoo authenticated uid=%d", self._uid)
        return self._uid

    def _search_read(self, model: str, domain: list, fields: list, limit: int = 200) -> list[dict]:
        uid = self._authenticate()
        return self._models.execute_kw(
            self.db, uid, self.password,
            model, "search_read",
            [domain],
            {"fields": fields, "limit": limit},
        )

    def load_products(self) -> list[DocumentChunk]:
        """ดึง product.template แปลงเป็น chunks"""
        records = self._search_read(
            "product.template",
            [["sale_ok", "=", True]],
            ["name", "description_sale", "list_price", "categ_id"],
        )
        chunks = []
        for r in records:
            name = r.get("name", "")
            desc = r.get("description_sale") or ""
            price = r.get("list_price", 0)
            categ = r.get("categ_id", [False, ""])[1] if r.get("categ_id") else ""

            content = f"## {name}\n"
            if categ:
                content += f"หมวดหมู่: {categ}\n"
            content += f"ราคา: {price:,.2f} บาท\n"
            if desc:
                content += f"\n{desc}"

            chunks.append(DocumentChunk(
                source="odoo:product.template",
                source_type="odoo",
                heading=name,
                content=content.strip(),
                topic="สินค้าและบริการ",
            ))

        logger.info("โหลด %d products จาก Odoo", len(chunks))
        return chunks

    def load_by_model(self, model: str) -> list[DocumentChunk]:
        """Generic loader — ดึง model ใดๆ แล้วแปลงเป็น plain text chunk"""
        records = self._search_read(model, [], ["display_name"])
        chunks = []
        for r in records:
            name = r.get("display_name") or str(r.get("id", ""))
            chunks.append(DocumentChunk(
                source=f"odoo:{model}",
                source_type="odoo",
                heading=name,
                content=name,
                topic=model,
            ))
        logger.info("โหลด %d records จาก Odoo model=%s", len(chunks), model)
        return chunks


def load_from_odoo(models: list[str] | None = None) -> list[DocumentChunk]:
    """Entry point — โหลดจาก env vars"""
    url = os.environ.get("ODOO_URL", "")
    db = os.environ.get("ODOO_DB", "")
    username = os.environ.get("ODOO_USERNAME", "")
    password = os.environ.get("ODOO_PASSWORD", "")

    if not all([url, db, username, password]):
        logger.warning("Odoo credentials ไม่ครบ — ข้าม Odoo sync")
        return []

    loader = OdooLoader(url, db, username, password)
    chunks: list[DocumentChunk] = []

    if not models:
        models = os.environ.get("ODOO_SYNC_MODELS", "product.template").split(",")

    for model in models:
        model = model.strip()
        if model == "product.template":
            chunks.extend(loader.load_products())
        else:
            chunks.extend(loader.load_by_model(model))

    return chunks
