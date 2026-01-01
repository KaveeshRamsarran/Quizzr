"""
Quiz Models
Quizzes, questions, attempts, and answers
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, Enum, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QuestionType(str, enum.Enum):
    """Type of quiz question"""
    MCQ = "mcq"  # Multiple choice (single answer)
    MULTI_SELECT = "multi_select"  # Multiple choice (multiple answers)
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"


class QuizDifficulty(str, enum.Enum):
    """Quiz difficulty level"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class Quiz(Base):
    """Quiz model"""
    __tablename__ = "quizzes"
    
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
    
    # Quiz info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Settings
    difficulty: Mapped[QuizDifficulty] = mapped_column(
        Enum(QuizDifficulty),
        default=QuizDifficulty.MIXED
    )
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pass_percentage: Mapped[int] = mapped_column(Integer, default=70)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True)
    show_explanations: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Question types included
    question_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Topics/sections included
    included_topics: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    excluded_topics: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Stats
    times_taken: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
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
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="quizzes")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="quizzes")
    source_document: Mapped[Optional["Document"]] = relationship("Document", back_populates="quizzes")
    questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan"
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Quiz(id={self.id}, name={self.name}, questions={self.question_count})>"


class QuizQuestion(Base):
    """Individual quiz question model"""
    __tablename__ = "quiz_questions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Question content
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType),
        default=QuestionType.MCQ
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Answer options (for MCQ, multi-select, matching)
    options: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    # Format: [{"id": "a", "text": "Option A"}, ...]
    
    # Correct answer(s)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    # For MCQ: "a" or "b" etc
    # For multi-select: ["a", "c"]
    # For true/false: "true" or "false"
    # For short answer: "expected answer"
    # For fill_blank: "missing word"
    # For matching: {"1": "a", "2": "b"} mapping
    
    # Explanation
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Difficulty
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    points: Mapped[int] = mapped_column(Integer, default=1)
    
    # Quality
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Source citations
    source_pages: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    source_snippets: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    source_chunk_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Topic/tag
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Order
    question_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Stats
    times_answered: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    tags: Mapped[List["QuestionTag"]] = relationship(
        "QuestionTag",
        back_populates="question",
        cascade="all, delete-orphan"
    )
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage"""
        if self.times_answered == 0:
            return 0.0
        return (self.times_correct / self.times_answered) * 100
    
    def __repr__(self) -> str:
        return f"<QuizQuestion(id={self.id}, type={self.question_type})>"


class QuizAttempt(Base):
    """User's attempt at a quiz"""
    __tablename__ = "quiz_attempts"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Score
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Percentage
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    points_possible: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Time tracking
    time_started: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    time_completed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Weak topics identified
    weak_topics: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")
    user: Mapped["User"] = relationship("User", back_populates="quiz_attempts")
    answers: Mapped[List["QuizAttemptAnswer"]] = relationship(
        "QuizAttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<QuizAttempt(id={self.id}, quiz_id={self.quiz_id}, score={self.score})>"


class QuizAttemptAnswer(Base):
    """Individual answer in a quiz attempt"""
    __tablename__ = "quiz_attempt_answers"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Answer
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    
    # Time
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    answered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    attempt: Mapped["QuizAttempt"] = relationship("QuizAttempt", back_populates="answers")
    
    def __repr__(self) -> str:
        return f"<QuizAttemptAnswer(id={self.id}, correct={self.is_correct})>"
