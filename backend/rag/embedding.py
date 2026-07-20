"""
rag/embedding.py
Embedding generation for the RAG pipeline. Primary path is Sentence Transformers
(all-MiniLM-L6-v2), per the spec.

Important, stated plainly: Sentence Transformers downloads its model weights from
the internet on first use. In network-restricted environments (e.g. this
development sandbox, some CI runners, or air-gapped deployments) that download
will fail. Rather than crash the whole RAG feature in that situation, this module
falls back to a TF-IDF vectorizer (scikit-learn, fully offline, no model download)
so the pipeline is still real, testable, and functional end-to-end.

This fallback is loudly logged and reported by is_using_fallback_embedder() —
it is never silently substituted. In a normal environment with internet access,
Sentence Transformers loads normally and this fallback path is never used.
"""

import os
import pickle
from typing import List

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_embedder = None  # lazily initialized singleton
_embedder_type = None  # "sentence_transformers" | "tfidf_fallback"

TFIDF_VECTORIZER_PATH = os.path.join(settings.chroma_persist_dir, "tfidf_vectorizer.pkl")


class SentenceTransformerEmbedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(settings.embedding_model)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()


class TfidfFallbackEmbedder:
    """
    Offline fallback. Must be *fit* once on the full document corpus (see
    fit_on_corpus) before it can embed queries consistently — TF-IDF vector
    dimensions depend on the fitted vocabulary, so the same fitted vectorizer
    is persisted to disk and reused for every subsequent query.
    """

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
        self._fitted = False

        if os.path.exists(TFIDF_VECTORIZER_PATH):
            with open(TFIDF_VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)
            self._fitted = True

    def fit_on_corpus(self, texts: List[str]) -> None:
        self.vectorizer.fit(texts)
        self._fitted = True
        os.makedirs(os.path.dirname(TFIDF_VECTORIZER_PATH), exist_ok=True)
        with open(TFIDF_VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError(
                "TfidfFallbackEmbedder used before fitting — call fit_on_corpus() "
                "during index build before embedding queries."
            )
        return self.vectorizer.transform(texts).toarray().tolist()


def get_embedder():
    """
    Returns a singleton embedder, preferring Sentence Transformers and falling
    back to TF-IDF if the model can't be loaded (e.g. no network access to
    download weights). The choice is cached for the process lifetime.
    """
    global _embedder, _embedder_type

    if _embedder is not None:
        return _embedder

    try:
        _embedder = SentenceTransformerEmbedder()
        _embedder_type = "sentence_transformers"
        logger.info(f"RAG embedder: sentence-transformers ({settings.embedding_model})")
    except Exception as exc:  # noqa: BLE001 — any failure (missing package, no network, etc.)
        logger.warning(
            f"Sentence Transformers unavailable ({exc}); falling back to TF-IDF "
            "embedder. This is expected in network-restricted environments. "
            "Install/verify internet access to sentence-transformers model weights "
            "to use real MiniLM embeddings instead."
        )
        _embedder = TfidfFallbackEmbedder()
        _embedder_type = "tfidf_fallback"

    return _embedder


def get_embedder_type() -> str:
    get_embedder()  # ensure initialized
    return _embedder_type


def is_using_fallback_embedder() -> bool:
    return get_embedder_type() == "tfidf_fallback"
