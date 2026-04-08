"""
Embedding generation and cosine similarity for memory retrieval.
"""

import hashlib
import logging
from dataclasses import dataclass

import numpy as np

from app.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

# In-process embedding cache: text_hash -> embedding vector
_embedding_cache: dict[str, list[float]] = {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def generate_embedding(
    text: str,
    client: GeminiClient | None = None,
    use_cache: bool = True,
) -> list[float]:
    """
    Generate a text embedding using Gemini text-embedding-004.
    Caches results to avoid re-computing unchanged texts.
    """
    key = _hash_text(text)
    if use_cache and key in _embedding_cache:
        return _embedding_cache[key]

    gemini = client or GeminiClient()
    embedding = await gemini.generate_embedding(text)

    if use_cache:
        _embedding_cache[key] = embedding

    return embedding


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    Returns float in [-1, 1]. Higher = more similar.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


@dataclass
class EpisodicMemory:
    tick: int
    summary: str
    emotional_valence: float = 0.0  # -1.0 (negative) to 1.0 (positive)
    importance_score: float = 0.5   # 0.0-1.0
    embedding: list[float] | None = None


async def find_relevant_memories(
    query: str,
    memories: list[EpisodicMemory],
    top_k: int = 5,
    client: GeminiClient | None = None,
) -> list[EpisodicMemory]:
    """
    Embed the query and return the top_k most relevant episodic memories
    by cosine similarity. Generates embeddings for memories that don't have one yet.
    """
    if not memories:
        return []

    gemini = client or GeminiClient()

    # Embed query
    query_embedding = await generate_embedding(query, client=gemini)

    # Ensure all memories have embeddings
    for memory in memories:
        if memory.embedding is None:
            memory.embedding = await generate_embedding(memory.summary, client=gemini)

    # Compute similarities
    scored = []
    for memory in memories:
        if memory.embedding:
            sim = cosine_similarity(query_embedding, memory.embedding)
            # Blend similarity with importance score
            combined_score = 0.7 * sim + 0.3 * memory.importance_score
            scored.append((combined_score, memory))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_memories = [m for _, m in scored[:top_k]]

    logger.debug(
        "Memory retrieval: query len=%d, %d/%d memories returned",
        len(query),
        len(top_memories),
        len(memories),
    )
    return top_memories
