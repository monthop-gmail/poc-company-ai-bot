"""
Company RAG MCP Server
FastMCP server exposing 2 tools: search_company_info, list_knowledge_topics

Health check: GET http://localhost:5001/health (background thread)
MCP endpoint: http://localhost:5000/mcp (FastMCP streamable-http)
"""

from __future__ import annotations

import argparse
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("company-rag")


@mcp.tool()
def search_company_info(query: str, topic_filter: str | None = None) -> list[dict]:
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
def list_knowledge_topics() -> list[str]:
    """
    ดูรายการหัวข้อที่มีข้อมูลอยู่ใน knowledge base

    Returns:
        รายชื่อ topics เช่น ["สินค้าและบริการ", "คำถามที่พบบ่อย", "นโยบาย"]
    """
    from .retriever import list_topics
    return list_topics()


def _start_health_server(port: int = 5001) -> None:
    """Health check server บน port แยก — ไม่ยุ่งกับ FastMCP internals"""
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass  # ปิด access log ไม่ให้รก

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("Health server started on port %d", port)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--health-port", type=int, default=5001)
    args = parser.parse_args()

    # Start health check server in background thread
    threading.Thread(
        target=_start_health_server,
        args=(args.health_port,),
        daemon=True,
    ).start()

    logger.info("Starting company-rag MCP server on %s:%d", args.host, args.port)
    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
