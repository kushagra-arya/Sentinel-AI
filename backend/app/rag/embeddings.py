"""Deterministic local embeddings for retrieval tests and offline operation."""

from collections import Counter
import hashlib
import math
import re


class HashingEmbeddingModel:
    """Small hashing vectorizer used without fine-tuning or external services."""

    token_pattern = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]+")

    def __init__(self, dimensions: int = 128) -> None:
        """Create a deterministic embedding model."""
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        """Embed text into a normalized hashing vector."""
        vector = [0.0] * self.dimensions
        tokens = [token.lower() for token in self.token_pattern.findall(text)]
        counts = Counter(tokens)
        for token, count in counts.items():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * float(count)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in stable order."""
        return [self.embed(text) for text in texts]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for normalized vectors."""
    return sum(a * b for a, b in zip(left, right, strict=True))
