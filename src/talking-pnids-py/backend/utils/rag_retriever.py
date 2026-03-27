"""
rag_retriever.py — Query-time RAG retrieval.

Loads the pre-built chunk+embedding index and retrieves top-k chunks
matching a query, filtered to a specific P&ID.

The index is loaded once at startup and cached in memory.
"""

import json
import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────

def _rag_dir() -> Path:
    """backend/utils/ → backend/ → talking-pnids-py/ → data/rag/"""
    return Path(__file__).resolve().parents[2] / "data" / "rag"


# ── Index loading ─────────────────────────────────────────────────────────────

_chunks: list[dict] | None = None
_embeddings: np.ndarray | None = None


def _load_index() -> tuple[list[dict], np.ndarray] | tuple[None, None]:
    global _chunks, _embeddings
    if _chunks is not None and _embeddings is not None:
        return _chunks, _embeddings

    rag_dir = _rag_dir()
    chunks_path = rag_dir / "chunks.json"
    embed_path  = rag_dir / "embeddings.npy"

    if not chunks_path.exists() or not embed_path.exists():
        return None, None

    _chunks     = json.loads(chunks_path.read_text())
    _embeddings = np.load(str(embed_path))
    return _chunks, _embeddings


def is_available() -> bool:
    """True if the RAG index has been built."""
    rag_dir = _rag_dir()
    return (rag_dir / "chunks.json").exists() and (rag_dir / "embeddings.npy").exists()


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed_query(query: str, api_key: str) -> np.ndarray:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=[query])
    return np.array(response.data[0].embedding, dtype=np.float32)


def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query_vec and each row of matrix."""
    q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    norms  = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    normed = matrix / norms
    return normed @ q_norm


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    pid_id: str,
    api_key: str,
    k: int = 5,
) -> list[dict]:
    """
    Retrieve top-k chunks relevant to `query` for the given `pid_id`.
    Returns list of {text, source, pid_tags, score}.
    Returns [] if index not available.
    """
    chunks, embeddings = _load_index()
    if chunks is None:
        return []

    # Filter to chunks tagged for this P&ID or global
    indices = [
        i for i, c in enumerate(chunks)
        if pid_id in c.get("pid_tags", []) or "global" in c.get("pid_tags", [])
    ]

    if not indices:
        return []

    # Embed query
    query_vec = _embed_query(query, api_key)

    # Cosine similarity over filtered subset
    subset_embeddings = embeddings[indices]
    scores = _cosine_similarity(query_vec, subset_embeddings)

    # Top-k
    top_k_local = min(k, len(indices))
    top_indices_local = np.argsort(scores)[::-1][:top_k_local]

    results = []
    for local_i in top_indices_local:
        global_i = indices[local_i]
        chunk = chunks[global_i]
        results.append({
            "text":     chunk["text"],
            "source":   chunk["source"],
            "pid_tags": chunk["pid_tags"],
            "score":    float(scores[local_i]),
        })

    return results


def format_for_prompt(chunks: list[dict], max_chars: int = 3000) -> str:
    """Format retrieved chunks into a prompt-ready string."""
    if not chunks:
        return ""

    parts = []
    total = 0
    for c in chunks:
        source = c.get("source", "unknown").replace(".docx", "")
        text   = c.get("text", "")
        entry  = f"[{source}]\n{text}"
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)

    return "\n\n---\n\n".join(parts)
