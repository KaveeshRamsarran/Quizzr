"""
Quiz Schemas
Request and response models for quiz-related endpoints
"""

from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, Field, computed_field, field_serializer
from pydantic.aliases import AliasChoices


class QuizQuestionCreate(BaseModel):
    """Schema for creating a quiz question"""
    question_type: str = Field(default="mcq")
    question_text: str = Field(min_length=1)
    # Tests may send options as list[str]; accept both.
    options: Optional[list] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    points: int = Field(default=1, ge=1)
    topic: Optional[str] = None
    source_pages: Optional[List[int]] = None
    source_snippets: Optional[List[str]] = None


class QuizQuestionUpdate(BaseModel):
    """Schema for updating a quiz question"""
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[dict]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    points: Optional[int] = Field(default=None, ge=1)
    topic: Optional[str] = None


class QuizQuestionResponse(BaseModel):
    """Schema for quiz question response"""
    id: int
    quiz_id: int
    question_type: str
    question_text: str
    options: Optional[List[dict]]
    difficulty: int
    points: int
    topic: Optional[str]
    question_order: int
    source_pages: Optional[List[int]]
    source_snippets: Optional[List[str]]
    needs_review: bool
    review_reason: Optional[str]
    
    # Hidden during quiz, shown after
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    
    # Stats
    times_answered: int = 0
    accuracy: float = 0.0
    
    class Config:
        from_attributes = True


class QuizCreate(BaseModel):
    """Schema for creating a quiz"""
    name: str = Field(min_length=1, max_length=255, validation_alias=AliasChoices("name", "title"))
    description: Optional[str] = None
    difficulty: str = Field(default="mixed")
    time_limit_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=180,
        validation_alias=AliasChoices("time_limit_minutes", "time_limit"),
    )
    pass_percentage: int = Field(default=70, ge=0, le=100, validation_alias=AliasChoices("pass_percentage", "passing_score"))
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_explanations: bool = True
    question_types: Optional[List[str]] = None
    course_id: Optional[int] = None


class QuizUpdate(BaseModel):
    """Schema for updating a quiz"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, validation_alias=AliasChoices("name", "title"))
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = Field(None, ge=1, le=180, validation_alias=AliasChoices("time_limit_minutes", "time_limit"))
    pass_percentage: Optional[int] = Field(None, ge=0, le=100, validation_alias=AliasChoices("pass_percentage", "passing_score"))
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    show_explanations: Optional[bool] = None
    course_id: Optional[int] = None


class QuizResponse(BaseModel):
    """Schema for quiz response"""
    id: int
    name: str
    description: Optional[str]
    difficulty: str
    time_limit_minutes: Optional[int]
    pass_percentage: int = 70
    question_count: int
    shuffle_questions: bool
    shuffle_options: bool
    show_explanations: bool
    question_types: Optional[List[str]]
    times_taken: int
    average_score: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    # Related
    course_id: Optional[int]
    source_document_id: Optional[int]
    
    class Config:
        from_attributes = True

    @field_serializer("difficulty")
    def serialize_difficulty(self, value):
        if hasattr(value, "value"):
            return value.value
        return str(value) if value is not None else "mixed"

    # Legacy/Frontend compatibility fields
    @computed_field
    @property
    def title(self) -> str:
        return self.name

    @computed_field
    @property
    def time_limit(self) -> Optional[int]:
        return self.time_limit_minutes

    @computed_field
    @property
    def passing_score(self) -> int:
        return self.pass_percentage

    @computed_field
    @property
    def document_id(self) -> Optional[int]:
        return self.source_document_id

    # Frontend compatibility: attempts_count = times_taken
    @computed_field
    @property
    def attempts_count(self) -> int:
        return self.times_taken

    # Frontend compatibility: best_score = average_score
    @computed_field
    @property
    def best_score(self) -> Optional[float]:
        return self.average_score


class QuizListResponse(BaseModel):
    """Schema for quiz list response"""
    quizzes: List[QuizResponse]
    total: int
    page: int
    limit: int
    pages: int

    @computed_field
    @property
    def items(self) -> List[QuizResponse]:
        return self.quizzes


class QuizDetailResponse(QuizResponse):
    """Schema for quiz detail with questions"""
    questions: List[QuizQuestionResponse] = []


# Alias for compatibility
QuizDetail = QuizDetailResponse


class QuizAttemptCreate(BaseModel):
    """Schema for starting a quiz attempt"""
    quiz_id: int


class QuizAnswerSubmit(BaseModel):
    """Schema for submitting an answer"""
    question_id: int
    answer: Any  # Can be string, list, or dict depending on question type
    # Tests send time_spent in ms
    time_spent_ms: Optional[int] = Field(default=None, validation_alias=AliasChoices("time_spent_ms", "time_spent"))


# Alias for compatibility
AnswerSubmission = QuizAnswerSubmit


class QuizAttemptResponse(BaseModel):
    """Schema for quiz attempt response"""
    id: int
    quiz_id: int
    is_completed: bool
    score: Optional[float]
    points_earned: int
    points_possible: int
    correct_count: int
    incorrect_count: int
    time_started: datetime
    time_completed: Optional[datetime]
    time_spent_seconds: Optional[int]
    
    # Current state
    current_question_index: int = 0
    answered_question_ids: List[int] = []
    
    class Config:
        from_attributes = True

    # Legacy field name used by tests
    @computed_field
    @property
    def completed(self) -> bool:
        return self.is_completed


# Alias for compatibility
QuizAttemptDetail = QuizAttemptResponse


class QuizAttemptAnswerResponse(BaseModel):
    """Schema for answer response after submission"""
    question_id: int
    user_answer: Any
    is_correct: bool
    points_earned: int
    correct_answer: str
    explanation: Optional[str]


class QuizResultResponse(BaseModel):
    """Schema for completed quiz result"""
    attempt_id: int
    quiz_id: int
    quiz_name: str
    score: float
    points_earned: int
    points_possible: int
    correct_count: int
    incorrect_count: int
    time_spent_seconds: int
    
    # Performance breakdown
    by_difficulty: dict = {}  # {"easy": {"correct": 5, "total": 6}, ...}
    by_topic: dict = {}  # {"topic1": {"correct": 3, "total": 5}, ...}
    by_type: dict = {}  # {"mcq": {"correct": 10, "total": 12}, ...}
    
    # Weak areas
    weak_topics: List[str] = []
    
    # Questions with answers
    questions: List[dict] = []

    # Legacy test fields
    completed: bool = True
    percentage: int = 0
    passed: bool = False


# Alias for compatibility
AttemptResultResponse = QuizResultResponse


class QuizFollowUpRequest(BaseModel):
    """Schema for generating follow-up quiz from mistakes"""
    attempt_id: int
    question_count: int = Field(default=10, ge=5, le=30)
