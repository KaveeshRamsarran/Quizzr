"""
Spaced Repetition Schedule Model
SM-2 algorithm implementation for flashcard scheduling
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpacedRepetitionSchedule(Base):
    """
    Spaced repetition schedule using SM-2 algorithm
    
    SM-2 Algorithm Parameters:
    - easiness: E-Factor (1.3 to 2.5+)
    - interval: Days until next review
    - repetitions: Number of successful reviews
    - quality: Last review quality (0-5)
    """
    __tablename__ = "spaced_repetition_schedules"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    card_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cards.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False
    )
    
    # SM-2 Parameters
    easiness: Mapped[float] = mapped_column(Float, default=2.5)  # E-Factor
    interval: Mapped[int] = mapped_column(Integer, default=1)  # Days
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Last review
    last_quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-5
    last_reviewed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Next review
    next_review: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        nullable=False
    )
    
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
    user: Mapped["User"] = relationship("User", back_populates="spaced_repetition_schedules")
    card: Mapped["Card"] = relationship("Card", back_populates="schedule")
    
    def update_schedule(self, quality: int) -> None:
        """
        Update schedule based on review quality using SM-2 algorithm
        
        Quality ratings:
        0 - Complete blackout
        1 - Incorrect, but remembered upon seeing answer
        2 - Incorrect, easy to recall after seeing answer
        3 - Correct with serious difficulty
        4 - Correct with some hesitation
        5 - Perfect response
        
        Maps from Quizzr ratings:
        - "Again" = 0
        - "Hard" = 2
        - "Good" = 4
        - "Easy" = 5
        """
        # Clamp quality to valid range
        quality = max(0, min(5, quality))
        
        # Update easiness factor
        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        self.easiness = max(
            1.3,
            self.easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )
        
        if quality < 3:
            # Failed review - reset repetitions
            self.repetitions = 0
            self.interval = 1
        else:
            # Successful review
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.easiness)
            
            self.repetitions += 1
        
        # Update timestamps
        self.last_quality = quality
        self.last_reviewed = datetime.utcnow()
        self.next_review = datetime.utcnow() + timedelta(days=self.interval)
        self.updated_at = datetime.utcnow()
    
    @property
    def is_due(self) -> bool:
        """Check if card is due for review"""
        return datetime.utcnow() >= self.next_review
    
    @property
    def days_until_review(self) -> int:
        """Days until next review (negative if overdue)"""
        delta = self.next_review - datetime.utcnow()
        return delta.days
    
    def __repr__(self) -> str:
        return f"<SpacedRepetitionSchedule(card_id={self.card_id}, interval={self.interval}, next={self.next_review})>"
