"""Document ingestion pipeline for regulated safety corpora."""

from hashlib import sha256
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import Document
from app.models.enums import DocumentType
from app.rag.chunking import ClausePreservingChunker, DocumentChunk
from app.rag.embeddings import HashingEmbeddingModel
from app.rag.vector_store import VectorStore


class DocumentIngestionPipeline:
    """Ingest PDF or text documents into PostgreSQL metadata and ChromaDB vectors."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_model: HashingEmbeddingModel | None = None,
        chunker: ClausePreservingChunker | None = None,
    ) -> None:
        """Create an ingestion pipeline with explicit dependencies."""
        self.vector_store = vector_store
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.chunker = chunker or ClausePreservingChunker()

    async def ingest_text(
        self,
        session: AsyncSession,
        *,
        title: str,
        document_type: DocumentType,
        source_uri: str,
        content_text: str,
        plant_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Persist text document metadata and index clause-preserving chunks."""
        checksum = sha256(content_text.encode("utf-8")).hexdigest()
        document = Document(
            plant_id=plant_id,
            title=title,
            document_type=document_type,
            source_uri=source_uri,
            checksum=checksum,
            content_text=content_text,
        )
        session.add(document)
        await session.flush()
        chunks = self.chunker.chunk(
            document_id=document.id,
            title=title,
            source_uri=source_uri,
            text=content_text,
        )
        embeddings = self.embedding_model.embed_many([chunk.text for chunk in chunks])
        self.vector_store.upsert(chunks, embeddings)
        await session.commit()
        return chunks

    async def ingest_file(
        self,
        session: AsyncSession,
        *,
        path: Path,
        title: str,
        document_type: DocumentType,
        plant_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Ingest a PDF or plaintext file from disk."""
        content_text = self._extract_text(path)
        return await self.ingest_text(
            session,
            title=title,
            document_type=document_type,
            source_uri=str(path),
            content_text=content_text,
            plant_id=plant_id,
        )

    @staticmethod
    def _extract_text(path: Path) -> str:
        """Extract text from supported document formats."""
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return path.read_text(encoding="utf-8")
