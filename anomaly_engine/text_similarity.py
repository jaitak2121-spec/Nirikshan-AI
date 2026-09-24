"""
TF-IDF vectorisation and cosine similarity, implemented on NumPy.

Why not scikit-learn: the only thing this prototype needs from it is a
`TfidfVectorizer` + `cosine_similarity` pair over ~30 short strings. That is
about sixty lines of NumPy, and writing it here keeps the duplicate-detection
maths fully visible to a reviewer instead of hidden behind a dependency.

The formulation deliberately matches scikit-learn's defaults so the numbers are
comparable to the standard implementation:

    tf       = raw term count in the document
    idf(t)   = ln((1 + n) / (1 + df(t))) + 1        (smooth_idf=True)
    weight   = tf * idf,  then L2-normalised per document
    cosine   = dot product of the L2-normalised vectors
"""

from __future__ import annotations

import math
import re

import numpy as np

# Matches scikit-learn's default token pattern: word characters, 2+ long.
_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")

# Pure function words only. Domain words such as "construction" are left in on
# purpose — IDF already discounts them, and removing them by hand would hide
# that behaviour from anyone auditing the score.
_STOPWORDS = {
    "of", "at", "the", "in", "for", "and", "to", "an", "on", "by",
    "with", "from", "under", "near", "as", "is", "are", "be",
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def build_tfidf_matrix(documents: list[str]) -> tuple[np.ndarray, list[str]]:
    """Return the L2-normalised TF-IDF matrix and its vocabulary."""
    tokenised = [tokenize(d) for d in documents]

    vocab: dict[str, int] = {}
    for tokens in tokenised:
        for token in tokens:
            if token not in vocab:
                vocab[token] = len(vocab)

    n_docs = len(documents)
    n_terms = len(vocab)
    if n_docs == 0 or n_terms == 0:
        return np.zeros((n_docs, 0)), []

    counts = np.zeros((n_docs, n_terms), dtype=np.float64)
    for row, tokens in enumerate(tokenised):
        for token in tokens:
            counts[row, vocab[token]] += 1.0

    # Document frequency -> smoothed IDF.
    df = (counts > 0).sum(axis=0)
    idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0

    tfidf = counts * idf

    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    tfidf = tfidf / norms

    inverse_vocab = [""] * n_terms
    for term, index in vocab.items():
        inverse_vocab[index] = term
    return tfidf, inverse_vocab


def cosine_similarity_matrix(matrix: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity of L2-normalised rows."""
    if matrix.size == 0:
        return np.zeros((matrix.shape[0], matrix.shape[0]))
    sim = matrix @ matrix.T
    return np.clip(sim, 0.0, 1.0)


def shared_terms(
    matrix: np.ndarray, vocab: list[str], i: int, j: int, limit: int = 6
) -> list[str]:
    """The terms contributing most to the similarity between rows i and j.

    Used as human-readable evidence: "these are the words the two records have
    in common", rather than asking an officer to trust a bare percentage.
    """
    if matrix.size == 0:
        return []
    contribution = matrix[i] * matrix[j]
    order = np.argsort(contribution)[::-1]
    out = []
    for index in order[:limit]:
        if contribution[index] <= 0:
            break
        out.append(vocab[index])
    return out


def haversine_km(
    lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None
) -> float | None:
    """Great-circle distance in kilometres, or None if any coordinate is absent."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0088  # mean Earth radius, km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = p2 - p1
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    )
    return round(2 * radius * math.asin(math.sqrt(a)), 4)
