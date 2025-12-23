"""
Deck and Card Models
Flashcard decks and individual cards
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, Enum, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeckType(str, enum.Enum):
    """Type of flashcard deck"""
    DEFINITIONS = "definitions"
    CONCEPTS = "concepts"
    PROCESSES = "processes"
    FORMULAS = "formulas"
    CLOZE = "cloze"
    PITFALLS = "pitfalls"
    MIXED = "mixed"


class CardType(str, enum.Enum):
    """Type of flashcard"""
    BASIC = "basic"  # Simple Q/A
    CLOZE = "cloze"  # Fill in blank
    DEFINITION = "definition"  # Term -> Definition
    CONCEPT = "concept"  # Concept -> Explanation
    PROCESS = "process"  # Steps/ordering
    FORMULA = "formula"  # Formula -> Usage
    ELI5 = "eli5"  # Explain like I'm 5
    DIAGRAM = "diagram"  # Diagram-based text


class Deck(Base):
    """Flashcard deck model"""
    __tablename__ = "decks"
    
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
    source_document_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    
    # Deck info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deck_type: Mapped[DeckType] = mapped_column(
        Enum(DeckType),
        default=DeckType.MIXED
    )
    
    # Settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    
    # Statistics
    card_count: Mapped[int] = mapped_column(Integer, default=0)
    mastered_count: Mapped[int] = mapped_column(Integer, default=0)
    
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
    last_studied: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="decks")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="decks")
    source_document: Mapped[Optional["Document"]] = relationship("Document", back_populates="decks")
    cards: Mapped[List["Card"]] = relationship(
        "Card",
        back_populates="deck",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Deck(id={self.id}, name={self.name}, cards={self.card_count})>"


class Card(Base):
    """Individual flashcard model"""
    __tablename__ = "cards"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    deck_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("decks.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Card content
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType),
        default=CardType.BASIC
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Additional content
    extra_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mnemonic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cloze-specific
    cloze_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cloze_answer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Difficulty and quality
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5 scale
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Source citations
    source_pages: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    source_snippets: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    source_chunk_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Study stats
    times_studied: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    times_incorrect: Mapped[int] = mapped_column(Integer, default=0)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    
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
    last_studied: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    deck: Mapped["Deck"] = relationship("Deck", back_populates="cards")
    tags: Mapped[List["CardTag"]] = relationship(
        "CardTag",
        back_populates="card",
        cascade="all, delete-orphan"
    )
    schedule: Mapped[Optional["SpacedRepetitionSchedule"]] = relationship(
        "SpacedRepetitionSchedule",
        back_populates="card",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage"""
        total = self.times_correct + self.times_incorrect
        if total == 0:
            return 0.0
        return (self.times_correct / total) * 100
    
    def __repr__(self) -> str:
        return f"<Card(id={self.id}, type={self.card_type}, difficulty={self.difficulty})>"
