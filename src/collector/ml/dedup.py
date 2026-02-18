"""Duplicate detection — TF-IDF + cosine similarity on canonical record titles/descriptions."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from collector.core.logging import get_logger

log = get_logger(__name__)


def build_corpus(
    records: list[dict[str, Any]],
    fields: tuple[str, ...] = ("title", "description"),
) -> list[str]:
    """Concatenate specified fields into a single text per record."""
    corpus: list[str] = []
    for rec in records:
        parts = [str(rec.get(f, "")) for f in fields]
        corpus.append(" ".join(parts).strip())
    return corpus


def find_duplicates(
    records: list[dict[str, Any]],
    threshold: float = 0.85,
    fields: tuple[str, ...] = ("title", "description"),
) -> list[tuple[int, int, float]]:
    """Return pairs of (index_a, index_b, similarity) that exceed *threshold*.

    Uses TF-IDF vectorization + cosine similarity.  For large corpora consider
    approximate nearest-neighbor approaches or sentence-transformer embeddings.
    """
    corpus = build_corpus(records, fields=fields)
    if len(corpus) < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=10_000)
    tfidf_matrix = vectorizer.fit_transform(corpus)

    sim_matrix = cosine_similarity(tfidf_matrix)
    np.fill_diagonal(sim_matrix, 0.0)

    duplicates: list[tuple[int, int, float]] = []
    seen: set[tuple[int, int]] = set()
    rows, cols = np.where(sim_matrix >= threshold)
    for i, j in zip(rows, cols, strict=True):
        pair = (min(i, j), max(i, j))
        if pair not in seen:
            seen.add(pair)
            duplicates.append((pair[0], pair[1], float(sim_matrix[i, j])))

    log.info("dedup.found", count=len(duplicates), threshold=threshold)
    return duplicates
