"""
Tag Models
Tags for organizing cards and questions
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tag(Base):
    """Tag model for categorizing content"""
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Usage count (denormalized for performance)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"


class CardTag(Base):
    """Many-to-many relationship between cards and tags"""
    __tablename__ = "card_tags"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    card: Mapped["Card"] = relationship("Card", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")
    
    def __repr__(self) -> str:
        return f"<CardTag(card_id={self.card_id}, tag_id={self.tag_id})>"


class QuestionTag(Base):
    """Many-to-many relationship between questions and tags"""
    __tablename__ = "question_tags"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")
    
    def __repr__(self) -> str:
        return f"<QuestionTag(question_id={self.question_id}, tag_id={self.tag_id})>"
