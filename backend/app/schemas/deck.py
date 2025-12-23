"""
Deck and Card Schemas
Request and response models for deck-related endpoints
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CardCreate(BaseModel):
    """Schema for creating a card"""
    card_type: str = Field(default="basic")
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)
    extra_explanation: Optional[str] = None
    example: Optional[str] = None
    mnemonic: Optional[str] = None
    cloze_text: Optional[str] = None
    cloze_answer: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    source_pages: Optional[List[int]] = None
    source_snippets: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CardUpdate(BaseModel):
    """Schema for updating a card"""
    front: Optional[str] = None
    back: Optional[str] = None
    extra_explanation: Optional[str] = None
    example: Optional[str] = None
    mnemonic: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    is_suspended: Optional[bool] = None
    needs_review: Optional[bool] = None
    tags: Optional[List[str]] = None


class CardResponse(BaseModel):
    """Schema for card response"""
    id: int
    deck_id: int
    card_type: str
    front: str
    back: str
    extra_explanation: Optional[str]
    example: Optional[str]
    mnemonic: Optional[str]
    cloze_text: Optional[str]
    cloze_answer: Optional[str]
    difficulty: int
    quality_score: Optional[float]
    needs_review: bool
    review_reason: Optional[str]
    source_pages: Optional[List[int]]
    source_snippets: Optional[List[str]]
    times_studied: int
    times_correct: int
    times_incorrect: int
    is_suspended: bool
    is_mastered: bool
    accuracy: float
    created_at: datetime
    last_studied: Optional[datetime]
    
    # Spaced repetition info
    next_review: Optional[datetime] = None
    interval_days: Optional[int] = None
    
    # Tags
    tags: List[str] = []
    
    class Config:
        from_attributes = True


class CardStudyRequest(BaseModel):
    """Schema for recording card study result"""
    rating: str = Field(..., pattern=r"^(again|hard|good|easy)$")
    time_spent_seconds: Optional[int] = None


# Alias for compatibility
CardReview = CardStudyRequest


class CardStudyResponse(BaseModel):
    """Schema for card study response"""
    card_id: int
    next_review: datetime
    interval_days: int
    easiness: float
    repetitions: int


# Alias for compatibility
CardReviewResponse = CardStudyResponse


class DeckCreate(BaseModel):
    """Schema for creating a deck"""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    deck_type: str = Field(default="mixed")
    course_id: Optional[int] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_public: bool = False


class DeckUpdate(BaseModel):
    """Schema for updating a deck"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    course_id: Optional[int] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_public: Optional[bool] = None


class DeckResponse(BaseModel):
    """Schema for deck response"""
    id: int
    name: str
    description: Optional[str]
    deck_type: str
    is_public: bool
    color: str
    card_count: int
    mastered_count: int
    created_at: datetime
    updated_at: datetime
    last_studied: Optional[datetime]
    
    # Related
    course_id: Optional[int]
    source_document_id: Optional[int]
    
    # Study stats
    due_count: int = 0
    new_count: int = 0
    
    class Config:
        from_attributes = True


class DeckListResponse(BaseModel):
    """Schema for deck list response"""
    decks: List[DeckResponse]
    total: int


class DeckDetailResponse(DeckResponse):
    """Schema for deck detail with cards"""
    cards: List[CardResponse] = []


# Alias for compatibility
DeckDetail = DeckDetailResponse


class DeckStudySession(BaseModel):
    """Schema for deck study session"""
    deck_id: int
    cards: List[CardResponse]
    total_cards: int
    new_cards: int
    review_cards: int
