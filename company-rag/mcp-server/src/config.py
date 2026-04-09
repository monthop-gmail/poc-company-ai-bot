import os

CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "/data/chroma")
BM25_INDEX_PATH = os.environ.get("BM25_INDEX_PATH", "/data/bm25/index.pkl")
COLLECTION_NAME = "company_knowledge"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

VECTOR_SEARCH_TOP_K = int(os.environ.get("VECTOR_SEARCH_TOP_K", "10"))
BM25_SEARCH_TOP_K = int(os.environ.get("BM25_SEARCH_TOP_K", "10"))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "5"))
HYBRID_WEIGHT_VECTOR = float(os.environ.get("HYBRID_WEIGHT_VECTOR", "0.6"))
HYBRID_WEIGHT_BM25 = float(os.environ.get("HYBRID_WEIGHT_BM25", "0.4"))
