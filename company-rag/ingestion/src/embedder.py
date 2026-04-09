"""
Embedder: embed DocumentChunk ลง ChromaDB + สร้าง BM25 index
ดัดแปลงจาก legal-th-suite/embedder.py
"""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .parser import DocumentChunk

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "/data/chroma")
BM25_INDEX_PATH = os.environ.get("BM25_INDEX_PATH", "/data/bm25/index.pkl")
COLLECTION_NAME = "company_knowledge"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


def _tokenize_thai(text: str) -> list[str]:
    """Tokenize สำหรับ BM25 — รองรับภาษาไทย"""
    try:
        from pythainlp.tokenize import word_tokenize
        return word_tokenize(text, engine="newmm", keep_whitespace=False)
    except Exception:
        return text.split()


def embed_chunks(chunks: list[DocumentChunk]) -> None:
    """Embed chunks ลง ChromaDB และสร้าง BM25 index"""
    if not chunks:
        logger.warning("ไม่มี chunks ให้ embed")
        return

    logger.info("กำลัง embed %d chunks...", len(chunks))

    # โหลด embedding model
    model = SentenceTransformer(EMBEDDING_MODEL)

    # สร้าง embeddings (prefix "passage:" สำหรับ multilingual-e5)
    texts = [f"passage: {c.content}" for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    # บันทึกลง ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # ลบ collection เก่าแล้วสร้างใหม่ (full re-index)
    client.delete_collection(COLLECTION_NAME)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": c.source,
            "source_type": c.source_type,
            "heading": c.heading,
            "topic": c.topic,
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=[c.content for c in chunks],
        metadatas=metadatas,
    )
    logger.info("บันทึก %d chunks ลง ChromaDB collection=%s", len(chunks), COLLECTION_NAME)

    # สร้าง BM25 index
    tokenized = [_tokenize_thai(c.content) for c in chunks]
    bm25 = BM25Okapi(tokenized)

    bm25_data = {
        "index": bm25,
        "corpus": [c.to_dict() for c in chunks],
        "tokenized": tokenized,
    }

    Path(BM25_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    logger.info("บันทึก BM25 index -> %s", BM25_INDEX_PATH)
