"""
Analytics Service
Study history, streaks, mastery and quiz performance.

Activity comes from two logs: card_review_logs (one row per flashcard review)
and quiz_attempt_answers (one row per answered question).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deck import Card, Deck
from app.models.document import Document
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
from app.models.spaced_repetition import CardReviewLog, SpacedRepetitionSchedule
from app.models.user import User

DAILY_GOAL = 20


def _day(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


class AnalyticsService:
    """Service for analytics and performance tracking"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    # Raw activity
    # ------------------------------------------------------------------ #

    async def _daily_activity(self, user_id: int, since: Optional[datetime] = None) -> Dict[date, dict]:
        """{day: {cards, cards_correct, questions, questions_correct, seconds}}"""
        days: Dict[date, dict] = defaultdict(lambda: {"cards": 0, "cards_correct": 0, "questions": 0, "questions_correct": 0, "seconds": 0.0})

        review_day = func.date(CardReviewLog.reviewed_at)
        q = select(
            review_day.label("d"),
            func.count(CardReviewLog.id),
            func.sum(case((CardReviewLog.quality >= 3, 1), else_=0)),
            func.coalesce(func.sum(CardReviewLog.time_spent_ms), 0),
        ).where(CardReviewLog.user_id == user_id)
        if since:
            q = q.where(CardReviewLog.reviewed_at >= since)
        for d, count, correct, ms in (await self.db.execute(q.group_by(review_day))).all():
            row = days[_day(d)]
            row["cards"] += count or 0
            row["cards_correct"] += correct or 0
            row["seconds"] += (ms or 0) / 1000

        answer_day = func.date(QuizAttemptAnswer.answered_at)
        q = (
            select(
                answer_day.label("d"),
                func.count(QuizAttemptAnswer.id),
                func.sum(case((QuizAttemptAnswer.is_correct == True, 1), else_=0)),  # noqa: E712
                func.coalesce(func.sum(QuizAttemptAnswer.time_spent_seconds), 0),
            )
            .join(QuizAttempt, QuizAttemptAnswer.attempt_id == QuizAttempt.id)
            .where(QuizAttempt.user_id == user_id)
        )
        if since:
            q = q.where(QuizAttemptAnswer.answered_at >= since)
        for d, count, correct, seconds in (await self.db.execute(q.group_by(answer_day))).all():
            row = days[_day(d)]
            row["questions"] += count or 0
            row["questions_correct"] += correct or 0
            row["seconds"] += seconds or 0
        return dict(days)

    @staticmethod
    def _streaks(active_days: List[date], today: date) -> tuple:
        if not active_days:
            return 0, 0
        days = sorted(set(active_days))
        longest = run = 1
        for prev, cur in zip(days, days[1:]):
            run = run + 1 if (cur - prev).days == 1 else 1
            longest = max(longest, run)
        current = 0
        cursor = today if days[-1] == today else today - timedelta(days=1)
        day_set = set(days)
        while cursor in day_set:
            current += 1
            cursor -= timedelta(days=1)
        return current, longest

    async def total_study_minutes(self, user_id: int) -> int:
        activity = await self._daily_activity(user_id)
        return int(sum(d["seconds"] for d in activity.values()) // 60)

    # ------------------------------------------------------------------ #
    # Overview
    # ------------------------------------------------------------------ #

    async def get_overview(self, user_id: int) -> dict:
        now = datetime.utcnow()
        today = now.date()
        end_of_today = datetime.combine(today + timedelta(days=1), datetime.min.time())

        user = await self.db.get(User, user_id)

        total_documents = (await self.db.execute(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        )).scalar() or 0
        total_decks = (await self.db.execute(
            select(func.count(Deck.id)).where(Deck.user_id == user_id)
        )).scalar() or 0
        total_quizzes = (await self.db.execute(
            select(func.count(Quiz.id)).where(Quiz.user_id == user_id)
        )).scalar() or 0

        card_counts = (await self.db.execute(
            select(
                func.count(Card.id),
                func.sum(case((Card.is_mastered == True, 1), else_=0)),  # noqa: E712
            ).join(Deck, Card.deck_id == Deck.id).where(Deck.user_id == user_id, Card.is_suspended == False)  # noqa: E712
        )).first()
        total_cards = card_counts[0] or 0
        cards_mastered = card_counts[1] or 0

        scheduled = (await self.db.execute(
            select(func.count(SpacedRepetitionSchedule.id))
            .join(Card, SpacedRepetitionSchedule.card_id == Card.id)
            .where(SpacedRepetitionSchedule.user_id == user_id, Card.is_suspended == False)  # noqa: E712
        )).scalar() or 0
        cards_new = max(0, total_cards - scheduled)
        cards_learning = max(0, total_cards - cards_new - cards_mastered)

        due_reviews = (await self.db.execute(
            select(func.count(SpacedRepetitionSchedule.id))
            .join(Card, SpacedRepetitionSchedule.card_id == Card.id)
            .where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.next_review < end_of_today,
                Card.is_suspended == False,  # noqa: E712
            )
        )).scalar() or 0

        quiz_perf = (await self.db.execute(
            select(func.count(QuizAttempt.id), func.avg(QuizAttempt.score)).where(
                QuizAttempt.user_id == user_id, QuizAttempt.is_completed == True  # noqa: E712
            )
        )).first()

        activity = await self._daily_activity(user_id)
        current_streak, longest_streak = self._streaks(list(activity.keys()), today)
        total_items = sum(d["cards"] + d["questions"] for d in activity.values())
        total_correct = sum(d["cards_correct"] + d["questions_correct"] for d in activity.values())
        total_seconds = sum(d["seconds"] for d in activity.values())

        week = [today - timedelta(days=i) for i in range(7)]
        recent_sessions = []
        for d in week:
            row = activity.get(d)
            if not row:
                continue
            items = row["cards"] + row["questions"]
            recent_sessions.append({
                "date": d,
                "duration_minutes": int(round(row["seconds"] / 60)),
                "cards_studied": row["cards"],
                "questions_answered": row["questions"],
                "accuracy": round((row["cards_correct"] + row["questions_correct"]) / items * 100, 1) if items else 0.0,
            })
        week_seconds = sum(activity.get(d, {}).get("seconds", 0) for d in week)

        last_activity = max(activity.keys()) if activity else None
        today_row = activity.get(today, {})

        return {
            "study_streak": current_streak,
            "longest_streak": longest_streak,
            "total_study_time_minutes": int(total_seconds // 60),
            "avg_daily_study_minutes": round(week_seconds / 60 / 7, 1),
            "total_documents": total_documents,
            "total_decks": total_decks,
            "total_cards": total_cards,
            "total_quizzes": total_quizzes,
            "cards_mastered": cards_mastered,
            "cards_learning": cards_learning,
            "cards_new": cards_new,
            "mastery_rate": round(cards_mastered / total_cards * 100, 1) if total_cards else 0.0,
            "overall_accuracy": round(total_correct / total_items * 100, 1) if total_items else 0.0,
            "cards_studied_today": today_row.get("cards", 0),
            "cards_due_today": due_reviews + cards_new,
            "reviews_due_today": due_reviews,
            "quizzes_taken": quiz_perf[0] or 0,
            "average_quiz_score": round(quiz_perf[1] or 0, 1),
            "last_study_date": datetime.combine(last_activity, datetime.min.time()) if last_activity else (user.last_study_date if user else None),
            "recent_sessions": recent_sessions,
        }

    # ------------------------------------------------------------------ #
    # Progress over time
    # ------------------------------------------------------------------ #

    async def get_study_progress(self, user_id: int, days: int = 30) -> dict:
        today = datetime.utcnow().date()
        days = max(7, min(int(days), 365))
        window_start = today - timedelta(days=max(days, 14) - 1)
        activity = await self._daily_activity(user_id, since=datetime.combine(window_start, datetime.min.time()))

        series = []
        for i in range(max(days, 14) - 1, -1, -1):
            d = today - timedelta(days=i)
            row = activity.get(d, {"cards": 0, "cards_correct": 0, "questions": 0, "questions_correct": 0, "seconds": 0})
            items = row["cards"] + row["questions"]
            series.append({
                "date": d.isoformat(),
                "cards": row["cards"],
                "questions": row["questions"],
                "minutes": round(row["seconds"] / 60, 1),
                "accuracy": round((row["cards_correct"] + row["questions_correct"]) / items * 100, 1) if items else 0.0,
                "items": items,
            })

        def summarize(rows):
            items = sum(r["items"] for r in rows)
            correct = sum(r["accuracy"] * r["items"] / 100 for r in rows)
            return items, (correct / items * 100 if items else 0.0), sum(r["minutes"] for r in rows)

        this_items, this_acc, this_min = summarize(series[-7:])
        last_items, last_acc, last_min = summarize(series[-14:-7])
        visible = series[-days:]
        goal_days = sum(1 for r in series[-7:] if r["cards"] >= DAILY_GOAL)

        return {
            "period": "week" if days <= 7 else "month" if days <= 31 else "all_time",
            "daily_stats": visible,
            "accuracy_trend": [r["accuracy"] for r in visible],
            "volume_trend": [r["items"] for r in visible],
            "this_week_vs_last": {
                "cards": this_items - last_items,
                "accuracy": round(this_acc - last_acc, 1),
                "time": round(this_min - last_min, 1),
                "this_week_items": this_items,
                "this_week_minutes": round(this_min, 1),
            },
            "daily_goal": DAILY_GOAL,
            "goal_completion_rate": round(goal_days / 7 * 100, 1),
        }

    # ------------------------------------------------------------------ #
    # Topics, missed questions, suggestions
    # ------------------------------------------------------------------ #

    async def get_topic_analytics(self, user_id: int, course_id: Optional[int] = None) -> dict:
        query = (
            select(
                QuizQuestion.topic,
                func.count(QuizAttemptAnswer.id).label("total"),
                func.sum(case((QuizAttemptAnswer.is_correct == True, 1), else_=0)).label("correct"),  # noqa: E712
                func.max(QuizAttemptAnswer.answered_at).label("last"),
            )
            .join(QuizAttemptAnswer, QuizQuestion.id == QuizAttemptAnswer.question_id)
            .join(QuizAttempt, QuizAttemptAnswer.attempt_id == QuizAttempt.id)
            .where(QuizAttempt.user_id == user_id, QuizQuestion.topic.isnot(None), QuizQuestion.topic != "")
            .group_by(QuizQuestion.topic)
        )
        topics, weak, strong = [], [], []
        for row in (await self.db.execute(query)).all():
            if not row.total:
                continue
            correct = row.correct or 0
            accuracy = correct / row.total * 100
            topics.append({
                "topic": row.topic,
                "total_items": row.total,
                "correct": correct,
                "incorrect": row.total - correct,
                "accuracy": round(accuracy, 1),
                "last_studied": row.last,
                "trend": "stable",
            })
            if accuracy < 70:
                weak.append(row.topic)
            elif accuracy >= 90:
                strong.append(row.topic)
        topics.sort(key=lambda t: t["accuracy"])
        return {"topics": topics, "weak_topics": weak, "strong_topics": strong, "recommended_review": weak[:5]}

    async def get_missed_questions(self, user_id: int, course_id: Optional[int] = None, limit: int = 10) -> dict:
        incorrect = func.sum(case((QuizAttemptAnswer.is_correct == False, 1), else_=0))  # noqa: E712
        query = (
            select(
                QuizQuestion.id,
                QuizQuestion.question_text,
                QuizQuestion.question_type,
                QuizQuestion.topic,
                Quiz.name.label("quiz_name"),
                func.count(QuizAttemptAnswer.id).label("total"),
                incorrect.label("incorrect"),
            )
            .join(QuizAttemptAnswer, QuizQuestion.id == QuizAttemptAnswer.question_id)
            .join(QuizAttempt, QuizAttemptAnswer.attempt_id == QuizAttempt.id)
            .join(Quiz, QuizQuestion.quiz_id == Quiz.id)
            .where(QuizAttempt.user_id == user_id)
            .group_by(QuizQuestion.id, Quiz.name)
            .having(incorrect > 0)
            .order_by(incorrect.desc())
            .limit(limit)
        )
        questions = []
        for row in (await self.db.execute(query)).all():
            wrong = row.incorrect or 0
            questions.append({
                "question_id": row.id,
                "question_text": row.question_text[:300],
                "question_type": row.question_type.value if hasattr(row.question_type, "value") else str(row.question_type),
                "times_incorrect": wrong,
                "times_correct": row.total - wrong,
                "accuracy": round((row.total - wrong) / row.total * 100, 1) if row.total else 0.0,
                "topic": row.topic,
                "source_document": row.quiz_name,
            })
        return {"questions": questions, "total": len(questions)}

    async def get_improvement_suggestions(self, user_id: int) -> List[dict]:
        suggestions: List[dict] = []
        overview = await self.get_overview(user_id)

        if overview["total_documents"] == 0:
            suggestions.append({
                "type": "get_started", "priority": "high", "title": "Upload your first PDF",
                "description": "Lecture notes, slides or a textbook chapter all work.", "action": "upload",
            })
        elif overview["total_decks"] == 0 and overview["total_quizzes"] == 0:
            suggestions.append({
                "type": "generate", "priority": "high", "title": "Make a deck from your document",
                "description": "Open the document and generate flashcards or a quiz.", "action": "open_documents",
            })

        due_deck = (await self.db.execute(
            select(Deck.id, Deck.name, func.count(SpacedRepetitionSchedule.id))
            .join(Card, Card.deck_id == Deck.id)
            .join(SpacedRepetitionSchedule, SpacedRepetitionSchedule.card_id == Card.id)
            .where(Deck.user_id == user_id, SpacedRepetitionSchedule.next_review <= datetime.utcnow())
            .group_by(Deck.id, Deck.name)
            .order_by(func.count(SpacedRepetitionSchedule.id).desc())
            .limit(1)
        )).first()
        if due_deck:
            suggestions.append({
                "type": "review_due", "priority": "high", "title": f"Review {due_deck[2]} cards in {due_deck[1]}",
                "description": "Reviewing on the day a card is due keeps the interval growing.",
                "action": "study_deck", "target_id": due_deck[0],
            })

        topics = await self.get_topic_analytics(user_id)
        if topics["weak_topics"]:
            topic = topics["weak_topics"][0]
            suggestions.append({
                "type": "weak_topic", "priority": "medium", "title": f"Revisit {topic}",
                "description": f"Your quiz accuracy on {topic} is under 70%.", "action": "take_quiz",
            })

        if overview["cards_new"] > 0 and not due_deck:
            suggestions.append({
                "type": "new_cards", "priority": "medium", "title": f"Learn {min(overview['cards_new'], 20)} new cards",
                "description": f"{overview['cards_new']} cards haven't been studied yet.", "action": "study_deck",
            })
        return suggestions
