"""
Document Models
Handles uploaded PDFs, extracted pages, and content chunks
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentStyle(str, enum.Enum):
    """Document style classification"""
    NOTES = "notes"  # Traditional lecture notes
    SLIDES = "slides"  # Presentation slides
    TEXTBOOK = "textbook"  # Textbook excerpts
    LAB = "lab"  # Lab manuals
    MIXED = "mixed"  # Mixed content


class ProcessingStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    COMPLETED = "completed"
    PROCESSED = "processed"  # Alias for completed
    FAILED = "failed"
    ERROR = "error"  # Alias for failed


# Alias for compatibility
DocumentStatus = ProcessingStatus


class Document(Base):
    """Uploaded PDF document model"""
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    
    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Bytes
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256
    
    # Document metadata
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Classification
    style: Mapped[DocumentStyle] = mapped_column(
        Enum(DocumentStyle),
        default=DocumentStyle.NOTES
    )
    
    # Processing status
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # OCR info
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_pages: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    
    # Extracted structure
    headings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    table_of_contents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="documents")
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number"
    )
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    decks: Mapped[List["Deck"]] = relationship(
        "Deck",
        back_populates="source_document"
    )
    quizzes: Mapped[List["Quiz"]] = relationship(
        "Quiz",
        back_populates="source_document"
    )
    
    @property
    def chunk_count(self) -> int:
        """Get count of chunks"""
        return len(self.chunks) if self.chunks else 0
    
    @property
    def deck_count(self) -> int:
        """Get count of decks"""
        return len(self.decks) if self.decks else 0
    
    @property
    def quiz_count(self) -> int:
        """Get count of quizzes"""
        return len(self.quizzes) if self.quizzes else 0
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.original_filename}, status={self.status})>"


class DocumentPage(Base):
    """Individual page from a document with extracted text"""
    __tablename__ = "document_pages"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Page info
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Content
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_length: Mapped[int] = mapped_column(Integer, default=0)
    
    # OCR
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Structure detected
    headings_on_page: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    has_tables: Mapped[bool] = mapped_column(Boolean, default=False)
    has_images: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    
    def __repr__(self) -> str:
        return f"<DocumentPage(doc_id={self.document_id}, page={self.page_number})>"


class Chunk(Base):
    """Study chunk - a meaningful unit of content for generation"""
    __tablename__ = "chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Position
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_page: Mapped[int] = mapped_column(Integer, nullable=False)
    end_page: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Context
    heading_context: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    parent_heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata
    key_terms: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    content_type: Mapped[str] = mapped_column(String(50), default="text")  # text, formula, definition, process
    
    # Generation tracking
    cards_generated: Mapped[int] = mapped_column(Integer, default=0)
    questions_generated: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    
    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, pages={self.start_page}-{self.end_page})>"
