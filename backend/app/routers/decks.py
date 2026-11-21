"""
Decks Router
Handles flashcard deck and card management
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models.user import User
from app.models.deck import Deck, Card
from app.models.course import Course
from app.models.spaced_repetition import SpacedRepetitionSchedule, CardReviewLog
from app.services.analytics import AnalyticsService
from app.schemas.deck import (
    DeckCreate, DeckUpdate, DeckResponse, DeckDetail, DeckListResponse,
    CardCreate, CardUpdate, CardResponse, CardReview, CardReviewResponse
)
from app.services.deck import DeckService
from app.services.spaced_repetition import SpacedRepetitionService
from app.routers.dependencies import get_current_user

router = APIRouter(tags=["Decks"])


async def _study_counts(session: AsyncSession, user_id: int, deck_ids: List[int]) -> dict:
    """{deck_id: (due_count, new_count)} for the given decks."""
    if not deck_ids:
        return {}
    now = datetime.utcnow()
    due_rows = await session.execute(
        select(Card.deck_id, func.count(SpacedRepetitionSchedule.id))
        .join(SpacedRepetitionSchedule, SpacedRepetitionSchedule.card_id == Card.id)
        .where(
            Card.deck_id.in_(deck_ids),
            Card.is_suspended == False,  # noqa: E712
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.next_review <= now,
        )
        .group_by(Card.deck_id)
    )
    scheduled = select(SpacedRepetitionSchedule.card_id).where(SpacedRepetitionSchedule.user_id == user_id)
    new_rows = await session.execute(
        select(Card.deck_id, func.count(Card.id))
        .where(Card.deck_id.in_(deck_ids), Card.is_suspended == False, ~Card.id.in_(scheduled))  # noqa: E712
        .group_by(Card.deck_id)
    )
    due = dict(due_rows.all())
    new = dict(new_rows.all())
    return {d: (due.get(d, 0), new.get(d, 0)) for d in deck_ids}


def _with_counts(model_cls, deck, counts: dict):
    data = model_cls.model_validate(deck)
    data.due_count, data.new_count = counts.get(deck.id, (0, 0))
    return data


def _safe_filename(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip()
    return cleaned[:80] or "deck"


@router.post("", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
async def create_deck(
    deck_data: DeckCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new flashcard deck
    """
    deck_service = DeckService(session)
    
    # Verify course if provided
    if deck_data.course_id:
        result = await session.execute(
            select(Course).where(
                Course.id == deck_data.course_id,
                Course.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    deck = await deck_service.create_deck(current_user.id, deck_data)
    return DeckResponse.model_validate(deck)


@router.get("", response_model=DeckListResponse)
@router.get("/", response_model=DeckListResponse)
async def list_decks(
    course_id: Optional[int] = None,
    document_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List user's flashcard decks
    """
    query = select(Deck).where(Deck.user_id == current_user.id)
    if document_id:
        query = query.where(Deck.source_document_id == document_id)
    
    if course_id:
        query = query.where(Deck.course_id == course_id)
    
    if search:
        query = query.where(
            Deck.name.ilike(f"%{search}%") |
            Deck.description.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count(Deck.id)).where(Deck.user_id == current_user.id)
    if document_id:
        count_query = count_query.where(Deck.source_document_id == document_id)
    if search:
        count_query = count_query.where(
            Deck.name.ilike(f"%{search}%") | Deck.description.ilike(f"%{search}%")
        )
    if course_id:
        count_query = count_query.where(Deck.course_id == course_id)
    
    total = (await session.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Deck.updated_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    decks = result.scalars().all()
    
    counts = await _study_counts(session, current_user.id, [d.id for d in decks])
    return DeckListResponse(
        decks=[_with_counts(DeckResponse, d, counts) for d in decks],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{deck_id}", response_model=DeckDetail)
async def get_deck(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get deck details including all cards
    """
    deck_service = DeckService(session)
    deck = await deck_service.get_deck(deck_id, current_user.id, include_cards=True)
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    counts = await _study_counts(session, current_user.id, [deck.id])
    return _with_counts(DeckDetail, deck, counts)


@router.put("/{deck_id}", response_model=DeckResponse)
async def update_deck(
    deck_id: int,
    deck_data: DeckUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update deck metadata
    """
    deck_service = DeckService(session)
    deck = await deck_service.update_deck(deck_id, current_user.id, deck_data)
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return DeckResponse.model_validate(deck)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a deck and all its cards
    """
    deck_service = DeckService(session)
    deleted = await deck_service.delete_deck(deck_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )


# Card endpoints

@router.post("/{deck_id}/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    deck_id: int,
    card_data: CardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Add a card to a deck
    """
    deck_service = DeckService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    card = await deck_service.create_card(deck_id, current_user.id, card_data)
    return CardResponse.model_validate(card)


@router.get("/{deck_id}/cards", response_model=List[CardResponse])
async def list_cards(
    deck_id: int,
    needs_review: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List all cards in a deck
    """
    deck_service = DeckService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    cards = await deck_service.get_deck_cards(deck_id, current_user.id)
    if needs_review is not None:
        cards = [c for c in cards if c.needs_review == needs_review]
    return [CardResponse.model_validate(c) for c in cards]


@router.put("/{deck_id}/cards/{card_id}", response_model=CardResponse)
async def update_card(
    deck_id: int,
    card_id: int,
    card_data: CardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a card's content
    """
    deck_service = DeckService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    card = await deck_service.update_card(card_id, current_user.id, card_data)
    if not card or card.deck_id != deck_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    return CardResponse.model_validate(card)


@router.delete("/{deck_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    deck_id: int,
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a card from a deck
    """
    deck_service = DeckService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    deleted = await deck_service.delete_card(card_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )


# Study endpoints

@router.get("/{deck_id}/study", response_model=List[CardResponse])
@router.get("/{deck_id}/due", response_model=List[CardResponse])
async def get_study_cards(
    deck_id: int,
    limit: int = Query(20, ge=1, le=200),
    mode: str = Query("due", pattern="^(due|all)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Cards to study now: cards due for review first, then cards never studied.
    mode=all returns every card in the deck (cram mode).
    """
    deck_service = DeckService(session)
    sr_service = SpacedRepetitionService(session)

    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )

    if mode == "all":
        cards = await deck_service.get_deck_cards(deck_id, current_user.id)
        cards = [c for c in cards if not c.is_suspended][:limit]
    else:
        cards = await sr_service.get_due_cards(current_user.id, deck_id, limit)
        if len(cards) < limit:
            cards += await sr_service.get_new_cards(current_user.id, deck_id, limit - len(cards))
    return [CardResponse.model_validate(c) for c in cards]


@router.post("/{deck_id}/cards/{card_id}/review", response_model=CardReviewResponse)
async def review_card(
    deck_id: int,
    card_id: int,
    review: CardReview,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit a review for a card (spaced repetition)
    Rating: again, hard, good, easy (or a raw SM-2 quality 0-5)
    """
    deck_service = DeckService(session)
    sr_service = SpacedRepetitionService(session)

    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )

    result = await session.execute(
        select(Card).where(Card.id == card_id, Card.deck_id == deck_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )

    if review.quality is not None:
        quality = int(review.quality)
    else:
        rating_map = {"again": 0, "hard": 3, "good": 4, "easy": 5}
        quality = rating_map.get((review.rating or "good"), 4)

    time_spent_ms = review.time_spent_ms
    if time_spent_ms is None and review.time_spent_seconds is not None:
        time_spent_ms = review.time_spent_seconds * 1000

    schedule = await sr_service.process_review(
        user_id=current_user.id,
        card_id=card_id,
        quality=quality,
        time_spent_ms=time_spent_ms,
    )

    # Study streak: consecutive calendar days with at least one review.
    now = datetime.utcnow()
    last = current_user.last_study_date
    today = now.date()
    if last is None or last.date() < today - timedelta(days=1):
        current_user.study_streak = 1
    elif last.date() == today - timedelta(days=1):
        current_user.study_streak = (current_user.study_streak or 0) + 1
    elif not current_user.study_streak:
        current_user.study_streak = 1
    current_user.last_study_date = now
    session.add(CardReviewLog(
        user_id=current_user.id,
        card_id=card_id,
        deck_id=deck_id,
        quality=quality,
        interval_days=schedule.interval,
        # Cap a single card at 5 minutes so an idle tab doesn't inflate study time.
        time_spent_ms=min(time_spent_ms, 300_000) if time_spent_ms else None,
        reviewed_at=now,
    ))
    await session.flush()
    current_user.total_study_time_minutes = await AnalyticsService(session).total_study_minutes(current_user.id)

    deck.last_studied = now
    deck.mastered_count = (await session.execute(
        select(func.count(Card.id)).where(Card.deck_id == deck_id, Card.is_mastered == True)  # noqa: E712
    )).scalar() or 0

    await session.commit()

    return CardReviewResponse(
        card_id=card_id,
        next_review=schedule.next_review,
        interval_days=schedule.interval,
        easiness=schedule.easiness,
        repetitions=schedule.repetitions,
    )


# Export endpoints

@router.get("/{deck_id}/export/csv")
@router.get("/{deck_id}/export")
async def export_deck_csv(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Export deck as CSV file
    """
    deck_service = DeckService(session)
    
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    csv_content = await deck_service.export_deck_csv(deck_id, current_user.id)
    if csv_content is None:
        csv_content = ""
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(deck.name)}.csv"'
        }
    )


@router.get("/{deck_id}/export/anki")
async def export_deck_anki(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Export deck in Anki-compatible format
    """
    deck_service = DeckService(session)
    
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    anki_content = await deck_service.export_deck_anki(deck_id, current_user.id) or ""
    
    return Response(
        content=anki_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(deck.name)}.txt"'
        }
    )
