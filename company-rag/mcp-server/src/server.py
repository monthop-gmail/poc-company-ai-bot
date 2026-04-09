"""
Company RAG MCP Server
FastMCP server exposing 2 tools: search_company_info, list_knowledge_topics

Health check: GET http://localhost:5000/health (ผ่าน custom_route)
MCP endpoint: http://localhost:5000/mcp
"""

import argparse
import logging
from typing import Optional

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("company-rag")


@mcp.tool()
def search_company_info(query: str, topic_filter: Optional[str] = None) -> list:
    """
    ค้นหาข้อมูลบริษัท สินค้า บริการ FAQ และนโยบาย

    Args:
        query: คำค้นหา เช่น "ราคาสินค้า", "นโยบายคืนสินค้า", "บริษัททำอะไร"
        topic_filter: กรองเฉพาะ topic เช่น "สินค้าและบริการ", "นโยบาย", "คำถามที่พบบ่อย"
                      ดู topics ที่มีทั้งหมดได้จาก list_knowledge_topics()
                      None = ค้นหาทุก topic

    Returns:
        รายการผลลัพธ์ที่เกี่ยวข้อง พร้อม heading, topic และ content
    """
    from .retriever import search
    results = search(query, topic_filter=topic_filter)
    if not results:
        return [{"content": "ไม่พบข้อมูลที่เกี่ยวข้อง", "heading": "", "topic": "", "source": ""}]
    return results


@mcp.tool()
def list_knowledge_topics() -> list:
    """
    ดูรายการหัวข้อที่มีข้อมูลอยู่ใน knowledge base

    Returns:
        รายชื่อ topics เช่น ["สินค้าและบริการ", "คำถามที่พบบ่อย", "นโยบาย"]
    """
    from .retriever import list_topics
    return list_topics()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    logger.info("Starting company-rag MCP server on %s:%d", args.host, args.port)
    app = mcp.streamable_http_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
