"""
Generation Schemas
Request and response models for AI generation endpoints
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DeckGenerationRequest(BaseModel):
    """Schema for deck generation request"""
    document_id: int
    
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


class QuizGenerationRequest(BaseModel):
    """Schema for quiz generation request"""
    document_id: int
    
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


class GenerationJobResponse(BaseModel):
    """Schema for generation job response"""
    job_id: int
    status: str
    job_type: str
    progress: float
    current_step: Optional[str]
    total_steps: int
    completed_steps: int
    
    # Result (when completed)
    result: Optional[dict] = None
    error_message: Optional[str] = None
    
    # Timing
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    
    class Config:
        from_attributes = True


# Alias for compatibility with routers
GenerationJobStatus = GenerationJobResponse


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
