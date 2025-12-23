"""
Analytics Schemas
Request and response models for analytics endpoints
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class StudySession(BaseModel):
    """Schema for a study session"""
    date: date
    duration_minutes: int
    cards_studied: int
    questions_answered: int
    accuracy: float


class TopicPerformance(BaseModel):
    """Schema for topic performance"""
    topic: str
    total_items: int
    correct: int
    incorrect: int
    accuracy: float
    last_studied: Optional[datetime]
    trend: str  # improving, declining, stable


class DifficultyBreakdown(BaseModel):
    """Schema for difficulty breakdown"""
    difficulty: int
    total: int
    mastered: int
    learning: int
    accuracy: float


class OverviewAnalytics(BaseModel):
    """Schema for overview analytics"""
    # Streak and time
    study_streak: int
    longest_streak: int
    total_study_time_minutes: int
    avg_daily_study_minutes: float
    
    # Content counts
    total_documents: int
    total_decks: int
    total_cards: int
    total_quizzes: int
    
    # Progress
    cards_mastered: int
    cards_learning: int
    cards_new: int
    mastery_rate: float  # Percentage of mastered cards
    
    # Performance
    overall_accuracy: float
    cards_studied_today: int
    cards_due_today: int
    quizzes_taken: int
    average_quiz_score: float
    
    # Recent activity
    last_study_date: Optional[datetime]
    recent_sessions: List[StudySession] = []


class TopicAnalytics(BaseModel):
    """Schema for topic analytics"""
    topics: List[TopicPerformance]
    weak_topics: List[str]  # Topics with < 70% accuracy
    strong_topics: List[str]  # Topics with > 90% accuracy
    recommended_review: List[str]  # Topics due for review


class StudyProgress(BaseModel):
    """Schema for study progress over time"""
    period: str  # week, month, all_time
    
    # Daily stats
    daily_stats: List[dict]  # {"date": "2024-01-01", "cards": 50, "accuracy": 0.85}
    
    # Trends
    accuracy_trend: List[float]  # Last 7/30 days
    volume_trend: List[int]  # Cards studied per day
    
    # Comparisons
    this_week_vs_last: dict  # {"cards": +50, "accuracy": +0.05, "time": +30}
    
    # Goals
    daily_goal: int
    goal_completion_rate: float


class QuestionAnalytics(BaseModel):
    """Schema for most missed questions"""
    question_id: int
    question_text: str
    question_type: str
    times_incorrect: int
    times_correct: int
    accuracy: float
    topic: Optional[str]
    source_document: Optional[str]


class CardAnalytics(BaseModel):
    """Schema for card performance analytics"""
    card_id: int
    front: str
    difficulty: int
    times_studied: int
    accuracy: float
    interval_days: int
    next_review: Optional[datetime]
    status: str  # new, learning, review, mastered


class ImprovementSuggestion(BaseModel):
    """Schema for improvement suggestion"""
    type: str  # weak_topic, low_accuracy, not_reviewed, exam_prep
    priority: str  # high, medium, low
    title: str
    description: str
    action: str  # study_deck, take_quiz, review_cards
    target_id: Optional[int] = None  # deck_id, quiz_id, etc.


class AnalyticsDashboard(BaseModel):
    """Schema for complete analytics dashboard"""
    overview: OverviewAnalytics
    topics: TopicAnalytics
    progress: StudyProgress
    most_missed_questions: List[QuestionAnalytics]
    struggling_cards: List[CardAnalytics]
    suggestions: List[ImprovementSuggestion]
