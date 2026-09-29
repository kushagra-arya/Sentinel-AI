"""Vector-store adapters for ChromaDB-backed retrieval."""

from dataclasses import dataclass
import math
from typing import Any, Protocol

from app.rag.chunking import DocumentChunk
from app.rag.embeddings import HashingEmbeddingModel, cosine_similarity


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk returned from vector retrieval with relevance score."""

    chunk: DocumentChunk
    score: float


class VectorStore(Protocol):
    """Protocol for document vector stores."""

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        """Store chunks and embeddings."""

    def query(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Return top matching chunks."""


class ChromaVectorStore:
    """ChromaDB vector store using deterministic local embeddings."""

    def __init__(self, *, chroma_url: str, collection_name: str) -> None:
        """Connect to a ChromaDB HTTP service by URL."""
        import chromadb

        host, port = self._parse_url(chroma_url)
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(collection_name)

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        """Upsert document chunks into ChromaDB."""
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "source_uri": chunk.source_uri,
                    "section": chunk.section,
                }
                for chunk in chunks
            ],
        )

    def query(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Query ChromaDB and map distances into bounded confidence scores."""
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        retrieved: list[RetrievedChunk] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=False,
        ):
            score = 1.0 / (1.0 + float(distance))
            retrieved.append(
                RetrievedChunk(
                    chunk=DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=str(metadata["document_id"]),
                        title=str(metadata["title"]),
                        source_uri=str(metadata["source_uri"]),
                        section=str(metadata["section"]),
                        text=document,
                    ),
                    score=score,
                )
            )
        return retrieved

    @staticmethod
    def _parse_url(chroma_url: str) -> tuple[str, int]:
        """Parse a simple Chroma URL into host and port."""
        stripped = chroma_url.removeprefix("http://").removeprefix("https://")
        host, _, port = stripped.partition(":")
        return host, int(port or "8000")


class InMemoryVectorStore:
    """In-memory vector store used for deterministic tests."""

    def __init__(self, embedding_model: HashingEmbeddingModel | None = None) -> None:
        """Create an empty in-memory vector index."""
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.entries: list[tuple[DocumentChunk, list[float]]] = []

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        """Store chunks and embeddings in memory."""
        existing = {chunk.chunk_id for chunk, _embedding in self.entries}
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if chunk.chunk_id not in existing:
                self.entries.append((chunk, embedding))

    def query(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Return top cosine-similar chunks."""
        scored = [
            RetrievedChunk(
                chunk=chunk,
                score=max(cosine_similarity(query_embedding, embedding), 0.0),
            )
            for chunk, embedding in self.entries
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def is_low_confidence(results: list[RetrievedChunk], min_confidence: float) -> bool:
    """Return whether retrieval evidence is too weak to ground an answer."""
    return not results or math.isclose(results[0].score, 0.0) or results[0].score < min_confidence
