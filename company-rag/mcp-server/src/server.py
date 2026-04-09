"""
Company RAG MCP Server
FastMCP server exposing 2 tools: search_company_info, list_knowledge_topics
"""

from __future__ import annotations

import argparse
import logging

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("company-rag")


@mcp.tool()
def search_company_info(query: str) -> list[dict]:
    """
    ค้นหาข้อมูลบริษัท สินค้า บริการ FAQ และนโยบาย

    Args:
        query: คำค้นหา เช่น "ราคาสินค้า", "นโยบายคืนสินค้า", "บริษัททำอะไร"

    Returns:
        รายการผลลัพธ์ที่เกี่ยวข้อง พร้อม heading, topic และ content
    """
    from .retriever import search
    results = search(query)
    if not results:
        return [{"content": "ไม่พบข้อมูลที่เกี่ยวข้อง", "heading": "", "topic": "", "source": ""}]
    return results


@mcp.tool()
def list_knowledge_topics() -> list[str]:
    """
    ดูรายการหัวข้อที่มีข้อมูลอยู่ใน knowledge base

    Returns:
        รายชื่อ topics เช่น ["สินค้าและบริการ", "คำถามที่พบบ่อย", "นโยบาย"]
    """
    from .retriever import list_topics
    return list_topics()


@mcp.resource("health://status")
def health() -> str:
    """Health check endpoint"""
    return "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    import uvicorn
    from mcp.server.fastmcp import FastMCP

    logger.info("Starting company-rag MCP server on %s:%d", args.host, args.port)
    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
