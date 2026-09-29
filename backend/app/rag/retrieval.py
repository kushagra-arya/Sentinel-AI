"""Retrieval service for grounded safety assistant answers."""

from app.core.config import Settings
from app.rag.embeddings import HashingEmbeddingModel
from app.rag.vector_store import ChromaVectorStore, RetrievedChunk, VectorStore, is_low_confidence


class RetrievalService:
    """Retrieve relevant safety document chunks from the vector store."""

    def __init__(
        self,
        *,
        settings: Settings,
        vector_store: VectorStore | None = None,
        embedding_model: HashingEmbeddingModel | None = None,
    ) -> None:
        """Create a retrieval service using ChromaDB unless a store is injected."""
        self.settings = settings
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.vector_store = vector_store or ChromaVectorStore(
            chroma_url=settings.chroma_url,
            collection_name=settings.chroma_collection,
        )

    def retrieve(self, query: str, *, top_k: int = 4) -> list[RetrievedChunk]:
        """Return relevant chunks for a query."""
        query_embedding = self.embedding_model.embed(query)
        return self.vector_store.query(query_embedding, top_k)

    def has_sufficient_evidence(self, results: list[RetrievedChunk]) -> bool:
        """Return whether retrieved results are strong enough to ground an answer."""
        return not is_low_confidence(results, self.settings.rag_min_confidence)
