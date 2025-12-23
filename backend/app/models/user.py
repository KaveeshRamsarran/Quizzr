"""
User Model
Handles user accounts, authentication, and preferences
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Enum, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    STANDARD = "standard"
    ADMIN = "admin"
    GUEST = "guest"


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    school: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Preferences
    preferred_difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5 scale
    study_goal_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Exam in X days
    simple_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # ELI5 explanations
    
    # Account status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), 
        default=UserRole.STANDARD,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
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
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Study statistics
    study_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_study_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_study_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Refresh token for JWT
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    courses: Mapped[List["Course"]] = relationship(
        "Course", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    decks: Mapped[List["Deck"]] = relationship(
        "Deck",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    quizzes: Mapped[List["Quiz"]] = relationship(
        "Quiz",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    spaced_repetition_schedules: Mapped[List["SpacedRepetitionSchedule"]] = relationship(
        "SpacedRepetitionSchedule",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    @property
    def is_guest(self) -> bool:
        """Check if user is a guest account"""
        return self.role == UserRole.GUEST
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
