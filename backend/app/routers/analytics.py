"""
Analytics Router
Handles user analytics and study statistics
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview, TopicAnalytics, StudyProgressResponse,
    MissedQuestionsResponse, ImprovementSuggestions
)
from app.services.analytics import AnalyticsService
from app.routers.dependencies import get_current_user

router = APIRouter(tags=["Analytics"])


@router.get("", response_model=AnalyticsOverview)
@router.get("/", response_model=AnalyticsOverview)
async def get_analytics_root(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Base analytics endpoint (alias of /overview)."""
    analytics_service = AnalyticsService(session)
    overview = await analytics_service.get_overview(current_user.id)
    return AnalyticsOverview(**overview)


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get overall study analytics and statistics
    """
    analytics_service = AnalyticsService(session)
    overview = await analytics_service.get_overview(current_user.id)
    return AnalyticsOverview(**overview)


@router.get("/topics", response_model=TopicAnalytics)
async def get_topic_analytics(
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get analytics broken down by topic/tag
    Shows strength and weakness areas
    """
    analytics_service = AnalyticsService(session)
    topics = await analytics_service.get_topic_analytics(current_user.id, course_id)
    return TopicAnalytics(**topics)


@router.get("/progress", response_model=StudyProgressResponse)
async def get_study_progress(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get study progress over time
    Returns daily activity data for charting
    """
    analytics_service = AnalyticsService(session)
    progress = await analytics_service.get_study_progress(current_user.id, days)
    return StudyProgressResponse(**progress)


@router.get("/missed-questions", response_model=MissedQuestionsResponse)
async def get_missed_questions(
    course_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get most frequently missed quiz questions
    Useful for targeted review
    """
    analytics_service = AnalyticsService(session)
    missed = await analytics_service.get_missed_questions(
        current_user.id, course_id, limit
    )
    return MissedQuestionsResponse(**missed)


@router.get("/suggestions", response_model=ImprovementSuggestions)
async def get_improvement_suggestions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get personalized improvement suggestions based on study patterns
    """
    analytics_service = AnalyticsService(session)
    suggestions = await analytics_service.get_improvement_suggestions(current_user.id)
    return ImprovementSuggestions(**suggestions)


@router.get("/streak")
async def get_streak_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current streak information
    """
    last_study_at = getattr(current_user, "last_study_date", None)
    current_streak = getattr(current_user, "study_streak", 0) or 0

    return {
        "current_streak": current_streak,
        # This project currently does not persist a separate "longest streak".
        # Return current streak for compatibility with the frontend.
        "longest_streak": current_streak,
        "last_study_at": last_study_at,
        "studied_today": bool(
            last_study_at and last_study_at.date() == datetime.utcnow().date()
        ),
    }


@router.get("/cards-due")
async def get_cards_due_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get count of cards due for review
    """
    from sqlalchemy import select, func
    from app.models.spaced_repetition import SpacedRepetitionSchedule
    
    now = datetime.utcnow()
    
    result = await session.execute(
        select(func.count(SpacedRepetitionSchedule.id)).where(
            SpacedRepetitionSchedule.user_id == current_user.id,
            SpacedRepetitionSchedule.next_review <= now
        )
    )
    due_count = result.scalar() or 0
    
    # Also get cards due in next 24 hours
    tomorrow = now + timedelta(days=1)
    upcoming_result = await session.execute(
        select(func.count(SpacedRepetitionSchedule.id)).where(
            SpacedRepetitionSchedule.user_id == current_user.id,
            SpacedRepetitionSchedule.next_review > now,
            SpacedRepetitionSchedule.next_review <= tomorrow
        )
    )
    upcoming_count = upcoming_result.scalar() or 0
    
    return {
        "due_now": due_count,
        "due_today": due_count + upcoming_count,
        "upcoming_24h": upcoming_count
    }
