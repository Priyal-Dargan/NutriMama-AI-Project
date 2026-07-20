"""
rag/loader.py
PDF loading and chunking for the RAG pipeline. Extracts text with PyPDF2, then
splits it into overlapping chunks sized for the embedding model's context window,
per the spec's PDF -> chunk -> embed -> store pipeline.
"""

import os
from typing import List, Dict

from PyPDF2 import PdfReader

from utils.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 30


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


def chunk_text(text: str, source_name: str) -> List[Dict[str, str]]:
    """
    Splits text into overlapping word-count chunks. Overlap preserves context
    across chunk boundaries so a fact split across two chunks is still retrievable.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    chunk_index = 0
    while start < len(words):
        end = start + CHUNK_SIZE_WORDS
        chunk_words = words[start:end]
        chunk_text_value = " ".join(chunk_words)
        chunks.append(
            {
                "id": f"{source_name}::chunk_{chunk_index}",
                "text": chunk_text_value,
                "source": source_name,
            }
        )
        chunk_index += 1
        start += CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS

    return chunks


def load_and_chunk_documents(documents_dir: str) -> List[Dict[str, str]]:
    """Loads every PDF in documents_dir, extracts text, and returns all chunks."""
    all_chunks: List[Dict[str, str]] = []

    if not os.path.isdir(documents_dir):
        logger.warning(f"Documents directory not found: {documents_dir}")
        return all_chunks

    pdf_files = [f for f in sorted(os.listdir(documents_dir)) if f.lower().endswith(".pdf")]
    if not pdf_files:
        logger.warning(f"No PDF files found in {documents_dir}")
        return all_chunks

    for filename in pdf_files:
        pdf_path = os.path.join(documents_dir, filename)
        try:
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text, source_name=filename)
            all_chunks.extend(chunks)
            logger.info(f"Loaded {filename}: {len(chunks)} chunk(s)")
        except Exception as exc:  # noqa: BLE001 — one bad PDF shouldn't stop ingestion of the rest
            logger.error(f"Failed to process {filename}: {exc}", exc_info=True)

    return all_chunks
