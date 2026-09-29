"""Document model for the safety assistant retrieval corpus."""

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import DocumentType, enum_values


class Document(TimestampMixin, Base):
    """Source document indexed for grounded assistant responses."""

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_plant_type", "plant_id", "document_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str | None] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    source_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)

    plant: Mapped["Plant | None"] = relationship()
