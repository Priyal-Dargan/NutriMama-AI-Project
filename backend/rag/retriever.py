"""
rag/retriever.py
Retrieval interface for the Medical Guidelines Agent (and Food Safety Agent
fallback). Backed by the real ChromaDB index built from rag/documents/ PDFs.
Returns an honest empty list if the index hasn't been built yet — callers
(agents/medical_agent.py) already handle "no documents retrieved" without
fabricating citations, so this module never needs to pretend.
"""

from typing import List, Dict

from config import settings
from rag.chromadb import query_index, index_stats
from utils.logger import get_logger

logger = get_logger(__name__)


def retrieve_relevant_documents(query: str, top_k: int = None) -> List[Dict[str, str]]:
    top_k = top_k or settings.rag_top_k
    try:
        results = query_index(query, top_k)
        logger.info(f"RAG retrieval: query='{query[:60]}...' -> {len(results)} chunk(s)")
        return results
    except Exception as exc:  # noqa: BLE001 — retrieval failure should degrade, not crash the chat flow
        logger.error(f"RAG retrieval failed: {exc}", exc_info=True)
        return []


def is_rag_index_ready() -> bool:
    try:
        return index_stats()["is_ready"]
    except Exception:
        return False
