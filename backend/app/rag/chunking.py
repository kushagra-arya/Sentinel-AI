"""Clause-preserving document chunking for regulated safety documents."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DocumentChunk:
    """A retrieval chunk with source and section metadata."""

    chunk_id: str
    document_id: str
    title: str
    source_uri: str
    section: str
    text: str


class ClausePreservingChunker:
    """Split documents by section or clause boundaries before size limits."""

    section_pattern = re.compile(
        r"(?im)^(section\s+\d+[a-z]?|clause\s+\d+(?:\.\d+)*|"
        r"chapter\s+\d+|oisd\s+\d+(?:\.\d+)*|sop\s+\d+(?:\.\d+)*)\b[:.\-\s]*(.*)$"
    )

    def __init__(self, max_chars: int = 1200) -> None:
        """Create a chunker with a maximum character budget per chunk."""
        self.max_chars = max_chars

    def chunk(
        self,
        *,
        document_id: str,
        title: str,
        source_uri: str,
        text: str,
    ) -> list[DocumentChunk]:
        """Return chunks that avoid splitting inside detected clauses where possible."""
        sections = self._split_sections(text)
        chunks: list[DocumentChunk] = []
        for section, section_text in sections:
            parts = self._split_large_section(section_text)
            for index, part in enumerate(parts, start=1):
                chunk_id = f"{document_id}:{section}:{index}".replace(" ", "_")
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        title=title,
                        source_uri=source_uri,
                        section=section,
                        text=part.strip(),
                    )
                )
        return [chunk for chunk in chunks if chunk.text]

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split source text at explicit section or clause headings."""
        matches = list(self.section_pattern.finditer(text))
        if not matches:
            return [("general", text.strip())]

        sections: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(1).strip()
            body = text[start:end].strip()
            sections.append((heading, body))
        return sections

    def _split_large_section(self, section_text: str) -> list[str]:
        """Split oversized sections on paragraph boundaries."""
        if len(section_text) <= self.max_chars:
            return [section_text]

        paragraphs = [paragraph.strip() for paragraph in section_text.split("\n\n")]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if not paragraph:
                continue
            candidate = f"{current}\n\n{paragraph}".strip()
            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks
