"""
rag/chromadb.py
ChromaDB persistence layer. Manages a single collection of embedded pregnancy
nutrition document chunks. Embeddings are computed explicitly via
rag/embedding.py and passed in — we don't use Chroma's built-in default
embedding function, since that also tries to download a model from the internet
at first use, which would hit the same network constraint this module already
handles explicitly and transparently in rag/embedding.py.
"""

import os
from typing import List, Dict

import chromadb

from config import settings
from rag.embedding import get_embedder, TfidfFallbackEmbedder
from rag.loader import load_and_chunk_documents
from utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "pregnancy_nutrition_docs"
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")

_client = None


def get_client():
    global _client
    if _client is None:
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection():
    client = get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def rebuild_index() -> Dict[str, int]:
    """
    Full rebuild: loads every PDF in rag/documents/, chunks it, embeds every
    chunk, and replaces the collection contents. Called by the admin endpoint
    (POST /admin/rag/rebuild-index) and can also be run standalone.
    """
    chunks = load_and_chunk_documents(DOCUMENTS_DIR)
    if not chunks:
        logger.warning("No document chunks found — index rebuild produced an empty collection.")
        return {"documents_processed": 0, "chunks_indexed": 0}

    embedder = get_embedder()

    # TF-IDF fallback must be fit on the full corpus before it can embed anything.
    if isinstance(embedder, TfidfFallbackEmbedder):
        embedder.fit_on_corpus([c["text"] for c in chunks])

    embeddings = embedder.embed([c["text"] for c in chunks])

    client = get_client()
    # Drop and recreate for a clean rebuild (avoids duplicate/stale chunks from prior runs).
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection may not exist yet on first run
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c["source"]} for c in chunks],
    )

    sources = {c["source"] for c in chunks}
    logger.info(f"RAG index rebuilt: {len(sources)} document(s), {len(chunks)} chunk(s)")
    return {"documents_processed": len(sources), "chunks_indexed": len(chunks)}


def query_index(query_text: str, top_k: int) -> List[Dict[str, str]]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    embedder = get_embedder()
    query_embedding = embedder.embed([query_text])[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=min(top_k, collection.count()))

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        output.append(
            {
                "source": meta.get("source", "unknown"),
                "snippet": doc[:400] + ("..." if len(doc) > 400 else ""),
                "distance": dist,
            }
        )
    return output


def index_stats() -> Dict:
    collection = get_collection()
    count = collection.count()
    return {
        "chunks_indexed": count,
        "is_ready": count > 0,
        "embedder_type": get_embedder().__class__.__name__,
    }
