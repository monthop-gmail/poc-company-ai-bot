"""
Retriever: Hybrid Search (Vector + BM25) + Reranking
ดัดแปลงจาก legal-th-suite/retriever.py
"""

from __future__ import annotations

import logging
import pickle
from typing import Any

import chromadb
from sentence_transformers import CrossEncoder, SentenceTransformer

from .config import (
    BM25_INDEX_PATH, BM25_SEARCH_TOP_K,
    CHROMA_PERSIST_DIR, COLLECTION_NAME,
    EMBEDDING_MODEL, HYBRID_WEIGHT_BM25, HYBRID_WEIGHT_VECTOR,
    RERANK_MODEL, RERANK_TOP_K, VECTOR_SEARCH_TOP_K,
)

logger = logging.getLogger(__name__)

_chroma_client = None
_collection = None
_embedding_model = None
_cross_encoder = None
_bm25_data: dict | None = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_collection(COLLECTION_NAME)
    return _collection


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(RERANK_MODEL)
    return _cross_encoder


def _get_bm25() -> dict:
    global _bm25_data
    if _bm25_data is None:
        with open(BM25_INDEX_PATH, "rb") as f:
            _bm25_data = pickle.load(f)
    return _bm25_data


def _tokenize(text: str) -> list[str]:
    try:
        from pythainlp.tokenize import word_tokenize
        return word_tokenize(text, engine="newmm", keep_whitespace=False)
    except Exception:
        return text.split()


def _reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion — รวม 2 ranked lists"""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + HYBRID_WEIGHT_VECTOR / (k + rank + 1)
        docs[doc_id] = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + HYBRID_WEIGHT_BM25 / (k + rank + 1)
        docs[doc_id] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs[doc_id] for doc_id, _ in ranked]


def search(query: str, top_k: int = RERANK_TOP_K, topic_filter: str | None = None) -> list[dict]:
    """Hybrid search: vector + BM25 + rerank

    Args:
        query: คำค้นหา
        top_k: จำนวนผลลัพธ์สูงสุด
        topic_filter: กรองเฉพาะ topic เช่น "สินค้าและบริการ", "นโยบาย" (None = ทุก topic)
    """
    # Vector search
    model = _get_embedding_model()
    query_embedding = model.encode(f"query: {query}", normalize_embeddings=True)

    collection = _get_collection()
    where = {"topic": topic_filter} if topic_filter else None
    vector_res = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=min(VECTOR_SEARCH_TOP_K, collection.count()),
        include=["documents", "metadatas", "distances"],
        where=where,
    )
    vector_docs = [
        {
            "id": vector_res["ids"][0][i],
            "content": vector_res["documents"][0][i],
            "metadata": vector_res["metadatas"][0][i],
        }
        for i in range(len(vector_res["ids"][0]))
    ]

    # BM25 search
    bm25_data = _get_bm25()
    bm25 = bm25_data["index"]
    corpus = bm25_data["corpus"]

    tokenized_query = _tokenize(query)
    bm25_scores = bm25.get_scores(tokenized_query)
    top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:BM25_SEARCH_TOP_K]

    bm25_docs = []
    for i in top_indices:
        if bm25_scores[i] <= 0:
            continue
        item = corpus[i]
        # type safety: รองรับทั้ง dict และ string (ป้องกัน schema drift)
        if isinstance(item, dict):
            content = item.get("content", str(item))
            meta = {
                "source": item.get("source", ""),
                "heading": item.get("heading", ""),
                "topic": item.get("topic", ""),
            }
        else:
            content = str(item)
            meta = {"source": "", "heading": "", "topic": ""}
        bm25_docs.append({"id": f"chunk_{i}", "content": content, "metadata": meta})

    # RRF fusion
    fused = _reciprocal_rank_fusion(vector_docs, bm25_docs)

    if not fused:
        return []

    # Rerank
    cross_encoder = _get_cross_encoder()
    pairs = [(query, doc["content"]) for doc in fused[:20]]
    rerank_scores = cross_encoder.predict(pairs)

    scored = sorted(
        zip(fused[:20], rerank_scores),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        {
            "content": doc["content"],
            "heading": doc["metadata"].get("heading", ""),
            "topic": doc["metadata"].get("topic", ""),
            "source": doc["metadata"].get("source", ""),
            "score": float(score),
        }
        for doc, score in scored[:top_k]
    ]


def list_topics() -> list[str]:
    """คืน topics ที่มีใน index"""
    collection = _get_collection()
    results = collection.get(include=["metadatas"])
    topics = sorted({m.get("topic", "") for m in results["metadatas"] if m.get("topic")})
    return topics
