"""
Pydantic Schemas Package
Request/Response validation models
"""

from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    TokenResponse, RefreshTokenRequest
)
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.schemas.document import (
    DocumentResponse, DocumentPageResponse, ChunkResponse,
    DocumentUploadResponse
)
from app.schemas.deck import (
    DeckCreate, DeckUpdate, DeckResponse,
    CardCreate, CardUpdate, CardResponse, CardStudyRequest
)
from app.schemas.quiz import (
    QuizCreate, QuizUpdate, QuizResponse,
    QuizQuestionResponse, QuizAttemptCreate, QuizAttemptResponse,
    QuizAnswerSubmit, QuizResultResponse
)
from app.schemas.generation import (
    DeckGenerationRequest, QuizGenerationRequest,
    GenerationJobResponse
)
from app.schemas.analytics import (
    OverviewAnalytics, TopicAnalytics, StudyProgress
)

__all__ = [
    # User
    "UserCreate", "UserLogin", "UserResponse", "UserUpdate",
    "TokenResponse", "RefreshTokenRequest",
    # Course
    "CourseCreate", "CourseUpdate", "CourseResponse",
    # Document
    "DocumentResponse", "DocumentPageResponse", "ChunkResponse",
    "DocumentUploadResponse",
    # Deck
    "DeckCreate", "DeckUpdate", "DeckResponse",
    "CardCreate", "CardUpdate", "CardResponse", "CardStudyRequest",
    # Quiz
    "QuizCreate", "QuizUpdate", "QuizResponse",
    "QuizQuestionResponse", "QuizAttemptCreate", "QuizAttemptResponse",
    "QuizAnswerSubmit", "QuizResultResponse",
    # Generation
    "DeckGenerationRequest", "QuizGenerationRequest",
    "GenerationJobResponse",
    # Analytics
    "OverviewAnalytics", "TopicAnalytics", "StudyProgress",
]
