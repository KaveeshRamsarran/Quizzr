"""
Generation Schemas
Request and response models for AI generation endpoints
"""

import enum
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator


class DeckGenerationRequest(BaseModel):
    """Schema for deck generation request"""
    document_id: int

    # Frontend compatibility
    title: Optional[str] = None
    card_count: Optional[int] = Field(default=None, ge=5, le=200)
    card_types: Optional[List[str]] = None  # basic|cloze|reverse (frontend)
    focus_topics: Optional[List[str]] = None
    
    # Deck settings
    name: Optional[str] = None  # Auto-generated if not provided
    deck_type: str = Field(default="mixed")  # definitions, concepts, processes, formulas, cloze, pitfalls, mixed
    course_id: Optional[int] = None
    
    # Content selection
    chunk_ids: Optional[List[int]] = None  # If None, use all chunks
    page_range: Optional[tuple] = None  # (start, end) pages
    topics: Optional[List[str]] = None  # Filter by topics
    
    # Generation settings
    max_cards: int = Field(default=50, ge=5, le=200)
    difficulty: str = Field(default="mixed")  # easy, medium, hard, mixed
    include_eli5: bool = False  # Include ELI5 explanations
    include_examples: bool = True
    include_mnemonics: bool = False
    
    # Card type toggles
    include_basic: bool = True
    include_cloze: bool = True
    include_definitions: bool = True
    include_concepts: bool = True
    include_processes: bool = True
    include_formulas: bool = True

    @model_validator(mode="after")
    def _apply_frontend_compat(self) -> "DeckGenerationRequest":
        # title -> name
        if not self.name and self.title:
            self.name = self.title

        # card_count -> max_cards (if provided)
        if self.card_count is not None:
            self.max_cards = self.card_count

        # focus_topics -> topics
        if self.focus_topics and not self.topics:
            self.topics = self.focus_topics

        # card_types -> include_* toggles (only if caller provided card_types)
        if self.card_types:
            normalized = {ct.lower() for ct in self.card_types}
            # Basic/cloze are the only ones supported explicitly by the current generator.
            self.include_basic = "basic" in normalized
            self.include_cloze = "cloze" in normalized
        return self


class QuizGenerationRequest(BaseModel):
    """Schema for quiz generation request"""
    document_id: int

    # Frontend compatibility
    title: Optional[str] = None
    focus_topics: Optional[List[str]] = None
    question_types: Optional[List[str]] = None  # multiple_choice|true_false|fill_blank|short_answer
    
    # Quiz settings
    name: Optional[str] = None  # Auto-generated if not provided
    course_id: Optional[int] = None
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=180)
    
    # Content selection
    chunk_ids: Optional[List[int]] = None
    page_range: Optional[tuple] = None
    topics: Optional[List[str]] = None
    
    # Generation settings
    question_count: int = Field(default=20, ge=5, le=50)
    difficulty: str = Field(default="mixed")  # easy, medium, hard, mixed
    
    # Question type toggles
    include_mcq: bool = True
    include_multi_select: bool = True
    include_true_false: bool = True
    include_short_answer: bool = True
    include_fill_blank: bool = True
    include_matching: bool = False  # More complex, optional
    
    # Additional options
    include_explanations: bool = True
    shuffle_questions: bool = True
    shuffle_options: bool = True

    @model_validator(mode="after")
    def _apply_frontend_compat(self) -> "QuizGenerationRequest":
        if not self.name and self.title:
            self.name = self.title

        if self.focus_topics and not self.topics:
            self.topics = self.focus_topics

        if self.question_types:
            normalized = {qt.lower() for qt in self.question_types}
            self.include_mcq = "multiple_choice" in normalized
            self.include_true_false = "true_false" in normalized
            self.include_fill_blank = "fill_blank" in normalized
            self.include_short_answer = "short_answer" in normalized
        return self


class GenerationJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationJobResponse(BaseModel):
    """Frontend-compatible generation job response"""

    job_id: int
    status: GenerationJobStatus
    message: Optional[str] = None
    progress: Optional[float] = None
    result_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class GenerationPreviewRequest(BaseModel):
    """Schema for previewing generation before running"""
    document_id: int
    chunk_ids: Optional[List[int]] = None
    page_range: Optional[tuple] = None


class GenerationPreviewResponse(BaseModel):
    """Schema for generation preview response"""
    document_id: int
    total_chunks: int
    selected_chunks: int
    estimated_cards: int
    estimated_questions: int
    estimated_time_seconds: int
    topics: List[str]
    warnings: List[str] = []


class VerificationResult(BaseModel):
    """Schema for verification result"""
    item_id: int
    item_type: str  # card or question
    is_verified: bool
    confidence: float
    issues: List[str] = []
    suggested_fix: Optional[str] = None
