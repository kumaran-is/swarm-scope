"""Tests for embedding utilities (no API key required)."""

import pytest

from app.gemini.embeddings import EpisodicMemory, cosine_similarity


def test_cosine_similarity_identical_vectors():
    vec = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_episodic_memory_dataclass():
    mem = EpisodicMemory(tick=5, summary="Something happened", emotional_valence=0.3, importance_score=0.8)
    assert mem.tick == 5
    assert mem.embedding is None
