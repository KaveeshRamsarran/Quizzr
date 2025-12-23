"""
Analytics Service
Study analytics and performance tracking
"""

from datetime import datetime, timedelta, date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.models.user import User
from app.models.deck import Deck, Card
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
from app.models.spaced_repetition import SpacedRepetitionSchedule
from app.models.document import Document


class AnalyticsService:
    """Service for analytics and performance tracking"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_overview(self, user_id: int) -> dict:
        """Get overview analytics for a user"""
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), datetime.min.time())
        week_ago = now - timedelta(days=7)
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        # Count documents
        doc_count = await self.db.execute(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        )
        total_documents = doc_count.scalar() or 0
        
        # Count decks and cards
        deck_result = await self.db.execute(
            select(
                func.count(Deck.id).label("deck_count"),
                func.sum(Deck.card_count).label("card_count"),
                func.sum(Deck.mastered_count).label("mastered_count")
            ).where(Deck.user_id == user_id)
        )
        deck_stats = deck_result.first()
        total_decks = deck_stats.deck_count or 0
        total_cards = deck_stats.card_count or 0
        cards_mastered = deck_stats.mastered_count or 0
        
        # Count quizzes
        quiz_count = await self.db.execute(
            select(func.count(Quiz.id)).where(Quiz.user_id == user_id)
        )
        total_quizzes = quiz_count.scalar() or 0
        
        # Quiz performance
        quiz_stats = await self.db.execute(
            select(
                func.count(QuizAttempt.id).label("attempts"),
                func.avg(QuizAttempt.score).label("avg_score")
            ).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.is_completed == True
            )
        )
        quiz_perf = quiz_stats.first()
        quizzes_taken = quiz_perf.attempts or 0
        average_quiz_score = round(quiz_perf.avg_score or 0, 1)
        
        # Cards due today
        due_result = await self.db.execute(
            select(func.count(SpacedRepetitionSchedule.id)).where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.next_review <= now
            )
        )
        cards_due_today = due_result.scalar() or 0
        
        # Cards studied today
        studied_today = await self.db.execute(
            select(func.count(SpacedRepetitionSchedule.id)).where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.last_reviewed >= today_start
            )
        )
        cards_studied_today = studied_today.scalar() or 0
        
        # New cards (no schedule)
        new_cards = total_cards - (await self.db.execute(
            select(func.count(SpacedRepetitionSchedule.id)).where(
                SpacedRepetitionSchedule.user_id == user_id
            )
        )).scalar() or 0
        
        # Learning cards (have schedule but not mastered)
        learning_cards = total_cards - cards_mastered - max(0, new_cards)
        
        # Calculate mastery rate
        mastery_rate = (cards_mastered / total_cards * 100) if total_cards > 0 else 0
        
        # Overall accuracy from quizzes
        accuracy_result = await self.db.execute(
            select(
                func.sum(QuizAttempt.correct_count).label("correct"),
                func.sum(QuizAttempt.correct_count + QuizAttempt.incorrect_count).label("total")
            ).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.is_completed == True
            )
        )
        acc = accuracy_result.first()
        if acc.total and acc.total > 0:
            overall_accuracy = round((acc.correct / acc.total) * 100, 1)
        else:
            overall_accuracy = 0.0
        
        # Recent sessions
        recent_sessions = await self._get_recent_sessions(user_id, days=7)
        
        # Calculate average daily study time
        if recent_sessions:
            avg_daily = sum(s["duration_minutes"] for s in recent_sessions) / len(recent_sessions)
        else:
            avg_daily = 0.0
        
        return {
            "study_streak": user.study_streak if user else 0,
            "longest_streak": user.study_streak if user else 0,  # Would need separate tracking
            "total_study_time_minutes": user.total_study_time_minutes if user else 0,
            "avg_daily_study_minutes": round(avg_daily, 1),
            "total_documents": total_documents,
            "total_decks": total_decks,
            "total_cards": total_cards,
            "total_quizzes": total_quizzes,
            "cards_mastered": cards_mastered,
            "cards_learning": max(0, learning_cards),
            "cards_new": max(0, new_cards),
            "mastery_rate": round(mastery_rate, 1),
            "overall_accuracy": overall_accuracy,
            "cards_studied_today": cards_studied_today,
            "cards_due_today": cards_due_today,
            "quizzes_taken": quizzes_taken,
            "average_quiz_score": average_quiz_score,
            "last_study_date": user.last_study_date if user else None,
            "recent_sessions": recent_sessions
        }
    
    async def _get_recent_sessions(
        self,
        user_id: int,
        days: int = 7
    ) -> List[dict]:
        """Get recent study sessions (approximated from card reviews and quiz attempts)"""
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        sessions = []
        
        for day in range(days):
            day_date = (now - timedelta(days=day)).date()
            day_start = datetime.combine(day_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            # Cards reviewed
            cards_result = await self.db.execute(
                select(func.count(SpacedRepetitionSchedule.id)).where(
                    SpacedRepetitionSchedule.user_id == user_id,
                    SpacedRepetitionSchedule.last_reviewed >= day_start,
                    SpacedRepetitionSchedule.last_reviewed < day_end
                )
            )
            cards_studied = cards_result.scalar() or 0
            
            # Quiz questions answered
            quiz_result = await self.db.execute(
                select(
                    func.count(QuizAttemptAnswer.id).label("answered"),
                    func.sum(case((QuizAttemptAnswer.is_correct == True, 1), else_=0)).label("correct")
                )
                .join(QuizAttempt)
                .where(
                    QuizAttempt.user_id == user_id,
                    QuizAttemptAnswer.answered_at >= day_start,
                    QuizAttemptAnswer.answered_at < day_end
                )
            )
            quiz_stats = quiz_result.first()
            questions_answered = quiz_stats.answered or 0
            questions_correct = quiz_stats.correct or 0
            
            if cards_studied > 0 or questions_answered > 0:
                total_items = cards_studied + questions_answered
                accuracy = (questions_correct / questions_answered * 100) if questions_answered > 0 else 0
                
                sessions.append({
                    "date": day_date.isoformat(),
                    "duration_minutes": total_items * 0.5,  # Estimate 30 sec per item
                    "cards_studied": cards_studied,
                    "questions_answered": questions_answered,
                    "accuracy": round(accuracy, 1)
                })
        
        return sessions
    
    async def get_topic_analytics(self, user_id: int, course_id: Optional[int] = None) -> dict:
        """Get performance analytics by topic"""
        # Get question performance by topic
        result = await self.db.execute(
            select(
                QuizQuestion.topic,
                func.count(QuizAttemptAnswer.id).label("total"),
                func.sum(case((QuizAttemptAnswer.is_correct == True, 1), else_=0)).label("correct")
            )
            .join(QuizAttemptAnswer, QuizQuestion.id == QuizAttemptAnswer.question_id)
            .join(QuizAttempt, QuizAttemptAnswer.attempt_id == QuizAttempt.id)
            .where(
                QuizAttempt.user_id == user_id,
                QuizQuestion.topic.isnot(None)
            )
            .group_by(QuizQuestion.topic)
        )
        
        topics = []
        weak_topics = []
        strong_topics = []
        
        for row in result:
            if row.topic and row.total > 0:
                accuracy = (row.correct / row.total) * 100
                
                topic_data = {
                    "topic": row.topic,
                    "total_items": row.total,
                    "correct": row.correct or 0,
                    "incorrect": row.total - (row.correct or 0),
                    "accuracy": round(accuracy, 1),
                    "last_studied": None,  # Would need to track
                    "trend": "stable"  # Would need historical data
                }
                topics.append(topic_data)
                
                if accuracy < 70:
                    weak_topics.append(row.topic)
                elif accuracy >= 90:
                    strong_topics.append(row.topic)
        
        # Sort by accuracy
        topics.sort(key=lambda x: x["accuracy"])
        
        return {
            "topics": topics,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "recommended_review": weak_topics[:5]
        }
    
    async def get_study_progress(
        self,
        user_id: int,
        days: int = 30
    ) -> dict:
        """Get study progress over time"""
        now = datetime.utcnow()
        
        daily_stats = []
        accuracy_trend = []
        volume_trend = []
        
        for day in range(days):
            day_date = (now - timedelta(days=day)).date()
            day_start = datetime.combine(day_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            # Get cards studied
            cards_result = await self.db.execute(
                select(func.count(SpacedRepetitionSchedule.id)).where(
                    SpacedRepetitionSchedule.user_id == user_id,
                    SpacedRepetitionSchedule.last_reviewed >= day_start,
                    SpacedRepetitionSchedule.last_reviewed < day_end
                )
            )
            cards = cards_result.scalar() or 0
            
            # Get accuracy
            acc_result = await self.db.execute(
                select(
                    func.sum(case((QuizAttemptAnswer.is_correct == True, 1), else_=0)).label("correct"),
                    func.count(QuizAttemptAnswer.id).label("total")
                )
                .join(QuizAttempt)
                .where(
                    QuizAttempt.user_id == user_id,
                    QuizAttemptAnswer.answered_at >= day_start,
                    QuizAttemptAnswer.answered_at < day_end
                )
            )
            acc = acc_result.first()
            
            if acc.total and acc.total > 0:
                accuracy = round((acc.correct / acc.total) * 100, 1)
            else:
                accuracy = None
            
            daily_stats.append({
                "date": day_date.isoformat(),
                "cards": cards,
                "accuracy": accuracy
            })
            
            if accuracy is not None:
                accuracy_trend.append(accuracy)
            volume_trend.append(cards)
        
        # Reverse to chronological order
        daily_stats.reverse()
        accuracy_trend.reverse()
        volume_trend.reverse()
        
        # Calculate week comparison
        this_week_cards = sum(volume_trend[-7:]) if len(volume_trend) >= 7 else sum(volume_trend)
        last_week_cards = sum(volume_trend[-14:-7]) if len(volume_trend) >= 14 else 0
        
        this_week_acc = sum(accuracy_trend[-7:]) / 7 if len(accuracy_trend) >= 7 else (
            sum(accuracy_trend) / len(accuracy_trend) if accuracy_trend else 0
        )
        last_week_acc = sum(accuracy_trend[-14:-7]) / 7 if len(accuracy_trend) >= 14 else 0
        
        return {
            "period": period,
            "daily_stats": daily_stats[-30:],  # Limit response size
            "accuracy_trend": accuracy_trend[-30:],
            "volume_trend": volume_trend[-30:],
            "this_week_vs_last": {
                "cards": this_week_cards - last_week_cards,
                "accuracy": round(this_week_acc - last_week_acc, 1),
                "time": 0  # Would need actual time tracking
            },
            "daily_goal": 20,  # Could be configurable
            "goal_completion_rate": min(100, (this_week_cards / (20 * 7)) * 100) if this_week_cards else 0
        }
    
    async def get_missed_questions(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        limit: int = 10
    ) -> dict:
        """Get most frequently missed questions"""
        questions = await self.get_most_missed_questions(user_id, limit)
        return {"questions": questions}
    
    async def get_most_missed_questions(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[dict]:
        """Get most frequently missed questions"""
        result = await self.db.execute(
            select(
                QuizQuestion.id,
                QuizQuestion.question_text,
                QuizQuestion.question_type,
                QuizQuestion.topic,
                func.count(QuizAttemptAnswer.id).label("total"),
                func.sum(case((QuizAttemptAnswer.is_correct == False, 1), else_=0)).label("incorrect")
            )
            .join(QuizAttemptAnswer, QuizQuestion.id == QuizAttemptAnswer.question_id)
            .join(QuizAttempt, QuizAttemptAnswer.attempt_id == QuizAttempt.id)
            .where(QuizAttempt.user_id == user_id)
            .group_by(QuizQuestion.id)
            .having(func.count(QuizAttemptAnswer.id) >= 2)  # At least 2 attempts
            .order_by(func.sum(case((QuizAttemptAnswer.is_correct == False, 1), else_=0)).desc())
            .limit(limit)
        )
        
        questions = []
        for row in result:
            accuracy = ((row.total - row.incorrect) / row.total) * 100 if row.total > 0 else 0
            questions.append({
                "question_id": row.id,
                "question_text": row.question_text[:200],  # Truncate for display
                "question_type": row.question_type.value,
                "times_incorrect": row.incorrect,
                "times_correct": row.total - row.incorrect,
                "accuracy": round(accuracy, 1),
                "topic": row.topic
            })
        
        return questions
    
    async def get_struggling_cards(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[dict]:
        """Get cards the user is struggling with"""
        result = await self.db.execute(
            select(Card, SpacedRepetitionSchedule)
            .join(SpacedRepetitionSchedule, Card.id == SpacedRepetitionSchedule.card_id)
            .join(Deck, Card.deck_id == Deck.id)
            .where(
                Deck.user_id == user_id,
                SpacedRepetitionSchedule.easiness < 2.0  # Low E-Factor indicates difficulty
            )
            .order_by(SpacedRepetitionSchedule.easiness)
            .limit(limit)
        )
        
        cards = []
        for card, schedule in result:
            accuracy = card.accuracy
            cards.append({
                "card_id": card.id,
                "front": card.front[:100],  # Truncate
                "difficulty": card.difficulty,
                "times_studied": card.times_studied,
                "accuracy": round(accuracy, 1),
                "interval_days": schedule.interval,
                "next_review": schedule.next_review,
                "status": "learning" if schedule.easiness < 2.0 else "review"
            })
        
        return cards
    
    async def get_improvement_suggestions(self, user_id: int) -> List[dict]:
        """Generate personalized improvement suggestions"""
        suggestions = []
        
        # Check for weak topics
        topic_analytics = await self.get_topic_analytics(user_id)
        weak_topics = topic_analytics.get("weak_topics", [])
        
        if weak_topics:
            suggestions.append({
                "type": "weak_topic",
                "priority": "high",
                "title": f"Review '{weak_topics[0]}'",
                "description": f"You're scoring below 70% on {weak_topics[0]}. Focus on this topic to improve.",
                "action": "study_deck",
                "target_id": None
            })
        
        # Check for cards due
        overview = await self.get_overview(user_id)
        due_count = overview.get("cards_due_today", 0)
        
        if due_count > 0:
            suggestions.append({
                "type": "review_due",
                "priority": "high",
                "title": f"Review {due_count} due cards",
                "description": "You have cards ready for review. Keeping up with reviews improves retention.",
                "action": "review_cards",
                "target_id": None
            })
        
        # Check for new cards
        new_cards = overview.get("cards_new", 0)
        if new_cards > 10:
            suggestions.append({
                "type": "new_cards",
                "priority": "medium",
                "title": "Learn new cards",
                "description": f"You have {new_cards} new cards to learn. Try learning 10-20 per day.",
                "action": "study_deck",
                "target_id": None
            })
        
        # Study streak encouragement
        streak = overview.get("study_streak", 0)
        if streak == 0:
            suggestions.append({
                "type": "streak",
                "priority": "medium",
                "title": "Start a study streak!",
                "description": "Study daily to build a streak. Consistency is key to learning.",
                "action": "study_deck",
                "target_id": None
            })
        
        return suggestions
