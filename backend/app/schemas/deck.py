"""
Deck and Card Schemas
Request and response models for deck-related endpoints
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_serializer, field_validator
from pydantic.aliases import AliasChoices
from pydantic import computed_field


class CardCreate(BaseModel):
    """Schema for creating a card"""
    card_type: str = Field(default="basic")
    front: str = Field(min_length=1, validation_alias=AliasChoices("front", "front_content"))
    back: str = Field(min_length=1, validation_alias=AliasChoices("back", "back_content"))
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
    front: Optional[str] = Field(default=None, validation_alias=AliasChoices("front", "front_content"))
    back: Optional[str] = Field(default=None, validation_alias=AliasChoices("back", "back_content"))
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

    @field_serializer("card_type")
    def serialize_card_type(self, value):
        if hasattr(value, "value"):
            return value.value
        return str(value) if value is not None else "basic"

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            if not value:
                return []
            if isinstance(value[0], str):
                return value
            # Card.tags is a list[CardTag]
            normalized: List[str] = []
            for item in value:
                tag_obj = getattr(item, "tag", None)
                tag_name = getattr(tag_obj, "name", None)
                if tag_name:
                    normalized.append(str(tag_name))
            return normalized
        return []

    # Legacy field names expected by tests
    @computed_field
    @property
    def front_content(self) -> str:
        return self.front

    @computed_field
    @property
    def back_content(self) -> str:
        return self.back


class CardStudyRequest(BaseModel):
    """Schema for recording card study result"""
    rating: Optional[str] = Field(default=None, pattern=r"^(again|hard|good|easy)$")
    quality: Optional[int] = Field(default=None, ge=0, le=5)
    time_spent_seconds: Optional[int] = None
    time_spent_ms: Optional[int] = None


# Alias for compatibility
CardReview = CardStudyRequest


class CardStudyResponse(BaseModel):
    """Schema for card study response"""
    card_id: int
    next_review: datetime
    interval_days: int
    easiness: float
    repetitions: int

    # Frontend/test compatibility
    @computed_field
    @property
    def next_review_at(self) -> datetime:
        return self.next_review

    @computed_field
    @property
    def ease_factor(self) -> float:
        return self.easiness


# Alias for compatibility
CardReviewResponse = CardStudyResponse


class DeckCreate(BaseModel):
    """Schema for creating a deck"""
    name: str = Field(min_length=1, max_length=255, validation_alias=AliasChoices("name", "title"))
    description: Optional[str] = None
    deck_type: str = Field(default="mixed")
    course_id: Optional[int] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_public: bool = False


class DeckUpdate(BaseModel):
    """Schema for updating a deck"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, validation_alias=AliasChoices("name", "title"))
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

    @field_serializer("deck_type")
    def serialize_deck_type(self, value):
        if hasattr(value, "value"):
            return value.value
        return str(value) if value is not None else "mixed"

    # Legacy/Frontend compatibility
    @computed_field
    @property
    def title(self) -> str:
        return self.name

    @computed_field
    @property
    def document_id(self) -> Optional[int]:
        return self.source_document_id


class DeckListResponse(BaseModel):
    """Schema for deck list response"""
    decks: List[DeckResponse]
    total: int
    page: int
    limit: int
    pages: int

    # Legacy alias expected by tests
    @computed_field
    @property
    def items(self) -> List[DeckResponse]:
        return self.decks


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
