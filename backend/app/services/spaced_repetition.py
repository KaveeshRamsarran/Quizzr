"""
Spaced Repetition Service
Implements SM-2 algorithm for flashcard scheduling
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.spaced_repetition import SpacedRepetitionSchedule
from app.models.deck import Card
from app.models.tag import CardTag


# Rating mappings
RATING_MAP = {
    "again": 0,
    "hard": 2,
    "good": 4,
    "easy": 5
}


class SpacedRepetitionService:
    """
    Service for spaced repetition scheduling using SM-2 algorithm
    
    SM-2 Algorithm Overview:
    1. Grade response 0-5 (0-2 = fail, 3-5 = pass)
    2. If fail: reset interval to 1, keep E-Factor
    3. If pass: 
       - First success: interval = 1
       - Second success: interval = 6
       - Subsequent: interval = prev_interval * E-Factor
    4. Update E-Factor: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    5. E-Factor minimum is 1.3
    """
    
    DEFAULT_EASE: float = 2.5
    MIN_EASE: float = 1.3

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    @classmethod
    def calculate_next_review(
        cls,
        *,
        quality: int,
        ease_factor: float,
        interval: int,
        repetitions: int,
    ) -> tuple[int, float]:
        """Pure SM-2 step.

        Returns:
            (new_interval_days, new_ease_factor)
        """
        q = max(0, min(5, int(quality)))
        ef = float(ease_factor)

        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        ef = max(
            cls.MIN_EASE,
            ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)),
        )

        if q < 3:
            # Failed review
            return 1, ef

        # Successful review
        reps = int(repetitions)
        prev_interval = int(interval)

        if reps <= 0:
            return 1, ef
        if reps == 1:
            return 6, ef

        # Mature cards
        next_interval = max(1, round(max(1, prev_interval) * ef))
        return next_interval, ef

    def _require_db(self) -> AsyncSession:
        if self.db is None:
            raise RuntimeError("SpacedRepetitionService requires a database session for this operation")
        return self.db
    
    async def get_or_create_schedule(
        self,
        user_id: int,
        card_id: int
    ) -> SpacedRepetitionSchedule:
        """Get existing schedule or create new one"""
        db = self._require_db()
        result = await db.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.card_id == card_id
            )
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            schedule = SpacedRepetitionSchedule(
                user_id=user_id,
                card_id=card_id,
                easiness=2.5,
                interval=1,
                repetitions=0,
                next_review=datetime.utcnow()
            )
            db.add(schedule)
            await db.flush()
            await db.refresh(schedule)
        
        return schedule
    
    async def record_review(
        self,
        user_id: int,
        card_id: int,
        rating: str
    ) -> SpacedRepetitionSchedule:
        """
        Record a card review and update schedule
        
        Args:
            user_id: User ID
            card_id: Card ID
            rating: One of "again", "hard", "good", "easy"
        
        Returns:
            Updated schedule
        """
        quality = RATING_MAP.get(rating.lower(), 4)
        
        schedule = await self.get_or_create_schedule(user_id, card_id)
        
        # Apply SM-2 algorithm
        schedule.update_schedule(quality)
        
        # Update card stats
        db = self._require_db()
        card_result = await db.execute(
            select(Card).where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()
        if card:
            card.times_studied += 1
            card.last_studied = datetime.utcnow()
            if quality >= 3:
                card.times_correct += 1
                if schedule.interval >= 21:  # 3 weeks = mastered
                    card.is_mastered = True
            else:
                card.times_incorrect += 1
                card.is_mastered = False
        
        await db.flush()
        await db.refresh(schedule)
        return schedule

    async def process_review(
        self,
        *,
        user_id: int,
        card_id: int,
        quality: int,
        time_spent_ms: int | None = None,
    ) -> SpacedRepetitionSchedule:
        """Compatibility alias expected by the decks router.

        Uses numeric SM-2 quality (0-5).
        """
        schedule = await self.get_or_create_schedule(user_id, card_id)

        # Apply SM-2 algorithm
        schedule.update_schedule(int(quality))

        # Update card stats
        db = self._require_db()
        card_result = await db.execute(select(Card).where(Card.id == card_id))
        card = card_result.scalar_one_or_none()
        if card:
            card.times_studied += 1
            card.last_studied = datetime.utcnow()
            if int(quality) >= 3:
                card.times_correct += 1
                if schedule.interval >= 21:
                    card.is_mastered = True
            else:
                card.times_incorrect += 1
                card.is_mastered = False

        await db.flush()
        await db.refresh(schedule)
        return schedule
    
    async def get_due_cards(
        self,
        user_id: int,
        deck_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Card]:
        """Get cards due for review"""
        now = datetime.utcnow()
        
        query = (
            select(Card)
            .join(SpacedRepetitionSchedule, Card.id == SpacedRepetitionSchedule.card_id)
            .where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.next_review <= now,
                Card.is_suspended == False
            )
        )

        query = query.options(selectinload(Card.tags).selectinload(CardTag.tag))
        
        if deck_id:
            query = query.where(Card.deck_id == deck_id)
        
        query = query.order_by(SpacedRepetitionSchedule.next_review).limit(limit)
        
        db = self._require_db()
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_new_cards(
        self,
        user_id: int,
        deck_id: int,
        limit: int = 20
    ) -> List[Card]:
        """Get new cards that haven't been studied yet"""
        # Get cards without a schedule for this user
        subquery = (
            select(SpacedRepetitionSchedule.card_id)
            .where(SpacedRepetitionSchedule.user_id == user_id)
        )
        
        db = self._require_db()
        result = await db.execute(
            select(Card)
            .where(
                Card.deck_id == deck_id,
                Card.is_suspended == False,
                ~Card.id.in_(subquery)
            )
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_study_session(
        self,
        user_id: int,
        deck_id: int,
        new_cards_limit: int = 10,
        review_cards_limit: int = 50
    ) -> dict:
        """
        Get cards for a study session
        
        Returns mix of new cards and review cards
        """
        # Get due cards
        due_cards = await self.get_due_cards(user_id, deck_id, review_cards_limit)
        
        # Get new cards
        new_cards = await self.get_new_cards(user_id, deck_id, new_cards_limit)
        
        # Interleave new and review cards
        all_cards = []
        new_idx = 0
        review_idx = 0
        
        # Add 1 new card every 5 review cards
        while new_idx < len(new_cards) or review_idx < len(due_cards):
            # Add up to 5 review cards
            for _ in range(5):
                if review_idx < len(due_cards):
                    all_cards.append(due_cards[review_idx])
                    review_idx += 1
            
            # Add 1 new card
            if new_idx < len(new_cards):
                all_cards.append(new_cards[new_idx])
                new_idx += 1
        
        return {
            "cards": all_cards,
            "new_count": len(new_cards),
            "review_count": len(due_cards),
            "total_count": len(all_cards)
        }
    
    async def get_deck_stats(
        self,
        user_id: int,
        deck_id: int
    ) -> dict:
        """Get spaced repetition statistics for a deck"""
        now = datetime.utcnow()
        
        # Count cards by status
        from sqlalchemy import func, case
        
        db = self._require_db()
        result = await db.execute(
            select(
                func.count(Card.id).label("total"),
                func.sum(case((Card.is_mastered == True, 1), else_=0)).label("mastered"),
                func.sum(case(
                    (SpacedRepetitionSchedule.next_review <= now, 1),
                    else_=0
                )).label("due")
            )
            .select_from(Card)
            .outerjoin(
                SpacedRepetitionSchedule,
                and_(
                    Card.id == SpacedRepetitionSchedule.card_id,
                    SpacedRepetitionSchedule.user_id == user_id
                )
            )
            .where(Card.deck_id == deck_id, Card.is_suspended == False)
        )
        
        stats = result.first()
        
        # Count new cards (no schedule)
        new_result = await db.execute(
            select(func.count(Card.id))
            .select_from(Card)
            .outerjoin(
                SpacedRepetitionSchedule,
                and_(
                    Card.id == SpacedRepetitionSchedule.card_id,
                    SpacedRepetitionSchedule.user_id == user_id
                )
            )
            .where(
                Card.deck_id == deck_id,
                Card.is_suspended == False,
                SpacedRepetitionSchedule.id == None
            )
        )
        new_count = new_result.scalar() or 0
        
        return {
            "total": stats.total or 0,
            "mastered": stats.mastered or 0,
            "due": stats.due or 0,
            "new": new_count,
            "learning": (stats.total or 0) - (stats.mastered or 0) - new_count
        }
    
    async def get_forecast(
        self,
        user_id: int,
        days: int = 7
    ) -> List[dict]:
        """Forecast reviews for the next N days"""
        now = datetime.utcnow()
        forecast = []
        
        for day in range(days):
            day_start = now + timedelta(days=day)
            day_end = day_start + timedelta(days=1)
            
            result = await self.db.execute(
                select(func.count(SpacedRepetitionSchedule.id))
                .where(
                    SpacedRepetitionSchedule.user_id == user_id,
                    SpacedRepetitionSchedule.next_review >= day_start,
                    SpacedRepetitionSchedule.next_review < day_end
                )
            )
            count = result.scalar() or 0
            
            forecast.append({
                "date": day_start.date().isoformat(),
                "count": count
            })
        
        return forecast
