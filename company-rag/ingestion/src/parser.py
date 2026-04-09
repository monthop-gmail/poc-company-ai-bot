"""
Parser: แยก markdown เป็น chunks ตาม heading
Chunking strategy: 1 heading section = 1 chunk

รองรับ:
- Markdown files (H1/H2/H3 headings)
- Plain text (paragraph-based chunking)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


@dataclass
class DocumentChunk:
    """หนึ่ง chunk = หนึ่ง section พร้อม metadata"""
    source: str          # ชื่อไฟล์ต้นทาง เช่น "faq.md"
    source_type: str     # "markdown" | "odoo"
    heading: str         # หัวข้อ section
    content: str         # เนื้อหาเต็ม (รวม heading)
    topic: str = ""      # หมวด เช่น "สินค้า", "FAQ", "นโยบาย"

    def to_dict(self) -> dict:
        return asdict(self)


def parse_markdown(path: str | Path, topic: str = "") -> list[DocumentChunk]:
    """แยก markdown file เป็น chunks ตาม heading"""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    source = path.name

    if not topic:
        topic = _detect_topic(source)

    chunks: list[DocumentChunk] = []
    splits = _HEADING.split(text)

    # splits = [before_first_heading, level, heading, content, level, heading, content, ...]
    # ถ้าไม่มี heading เลย → chunk เดียว
    if len(splits) == 1:
        content = splits[0].strip()
        if content:
            chunks.append(DocumentChunk(
                source=source,
                source_type="markdown",
                heading=path.stem,
                content=content,
                topic=topic,
            ))
        return chunks

    # ส่วนก่อน heading แรก
    preamble = splits[0].strip()
    if preamble:
        chunks.append(DocumentChunk(
            source=source,
            source_type="markdown",
            heading=path.stem,
            content=preamble,
            topic=topic,
        ))

    # each group: (level, heading, content)
    it = iter(splits[1:])
    for level, heading, content in zip(it, it, it):
        heading = heading.strip()
        content = content.strip()
        if not content and not heading:
            continue
        full_text = f"{'#' * len(level)} {heading}\n{content}".strip()
        chunks.append(DocumentChunk(
            source=source,
            source_type="markdown",
            heading=heading,
            content=full_text,
            topic=topic,
        ))

    logger.info("แยกได้ %d chunks จาก %s", len(chunks), source)
    return chunks


def _detect_topic(filename: str) -> str:
    """เดา topic จากชื่อไฟล์"""
    mapping = {
        "about": "เกี่ยวกับบริษัท",
        "products": "สินค้าและบริการ",
        "faq": "คำถามที่พบบ่อย",
        "policies": "นโยบาย",
    }
    stem = Path(filename).stem.lower()
    for key, topic in mapping.items():
        if key in stem:
            return topic
    return stem
