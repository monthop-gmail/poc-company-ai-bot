"""
Pipeline CLI: ingest --source markdown|odoo|all
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .parser import parse_markdown, DocumentChunk
from .odoo_loader import load_from_odoo
from .embedder import embed_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path("/knowledge")


def ingest_markdown() -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    md_files = list(KNOWLEDGE_DIR.glob("**/*.md"))
    if not md_files:
        logger.warning("ไม่พบ .md files ใน %s", KNOWLEDGE_DIR)
        return chunks
    for f in md_files:
        chunks.extend(parse_markdown(f))
    logger.info("รวม %d chunks จาก %d markdown files", len(chunks), len(md_files))
    return chunks


def ingest_odoo() -> list[DocumentChunk]:
    return load_from_odoo()


def main():
    parser = argparse.ArgumentParser(description="Company RAG Ingestion Pipeline")
    sub = parser.add_subparsers(dest="command")

    ingest_cmd = sub.add_parser("ingest", help="Ingest data into ChromaDB")
    ingest_cmd.add_argument(
        "--source",
        choices=["markdown", "odoo", "all"],
        default="all",
        help="แหล่งข้อมูลที่ต้องการ ingest",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        chunks: list[DocumentChunk] = []

        if args.source in ("markdown", "all"):
            chunks.extend(ingest_markdown())

        if args.source in ("odoo", "all"):
            chunks.extend(ingest_odoo())

        if not chunks:
            logger.error("ไม่มีข้อมูลให้ ingest")
            return

        logger.info("รวมทั้งหมด %d chunks — เริ่ม embed...", len(chunks))
        embed_chunks(chunks)
        logger.info("Ingestion เสร็จสมบูรณ์")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
