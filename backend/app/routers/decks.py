"""
Decks Router
Handles flashcard deck and card management
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models.user import User
from app.models.deck import Deck, Card
from app.models.course import Course
from app.models.spaced_repetition import SpacedRepetitionSchedule
from app.schemas.deck import (
    DeckCreate, DeckUpdate, DeckResponse, DeckDetail, DeckListResponse,
    CardCreate, CardUpdate, CardResponse, CardReview, CardReviewResponse
)
from app.services.deck import DeckService
from app.services.spaced_repetition import SpacedRepetitionService
from app.routers.dependencies import get_current_user

router = APIRouter(tags=["Decks"])


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


@router.get("/", response_model=DeckListResponse)
async def list_decks(
    course_id: Optional[int] = None,
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
    
    if course_id:
        query = query.where(Deck.course_id == course_id)
    
    if search:
        query = query.where(
            Deck.title.ilike(f"%{search}%") |
            Deck.description.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count(Deck.id)).where(Deck.user_id == current_user.id)
    if course_id:
        count_query = count_query.where(Deck.course_id == course_id)
    
    total = (await session.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Deck.updated_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    decks = result.scalars().all()
    
    return DeckListResponse(
        decks=[DeckResponse.model_validate(d) for d in decks],
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
    deck = await deck_service.get_deck(deck_id, current_user.id)
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return DeckDetail.model_validate(deck)


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
    
    card = await deck_service.create_card(deck_id, card_data)
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
    
    query = select(Card).where(Card.deck_id == deck_id)
    
    if needs_review is not None:
        query = query.where(Card.needs_review == needs_review)
    
    query = query.order_by(Card.order_index)
    
    result = await session.execute(query)
    cards = result.scalars().all()
    
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
    
    card = await deck_service.update_card(card_id, card_data)
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
    
    deleted = await deck_service.delete_card(card_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )


# Study endpoints

@router.get("/{deck_id}/study", response_model=List[CardResponse])
async def get_study_cards(
    deck_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get cards due for study based on spaced repetition schedule
    """
    deck_service = DeckService(session)
    sr_service = SpacedRepetitionService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    cards = await sr_service.get_due_cards(current_user.id, deck_id, limit)
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
    Rating: again (0), hard (1), good (2), easy (3)
    """
    deck_service = DeckService(session)
    sr_service = SpacedRepetitionService(session)
    
    # Verify deck ownership
    deck = await deck_service.get_deck(deck_id, current_user.id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Verify card exists in deck
    result = await session.execute(
        select(Card).where(Card.id == card_id, Card.deck_id == deck_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Map rating string to quality value
    rating_map = {"again": 0, "hard": 1, "good": 2, "easy": 3}
    quality = rating_map.get(review.rating, 2)
    
    # Process review
    schedule = await sr_service.process_review(
        user_id=current_user.id,
        card_id=card_id,
        quality=quality,
        time_spent_ms=review.time_spent_ms
    )
    
    # Update user study stats
    current_user.total_cards_studied += 1
    current_user.last_study_at = datetime.utcnow()
    
    # Update streak if first study today
    today = datetime.utcnow().date()
    if current_user.last_study_at is None or current_user.last_study_at.date() < today:
        current_user.current_streak += 1
        if current_user.current_streak > current_user.longest_streak:
            current_user.longest_streak = current_user.current_streak
    
    await session.commit()
    
    return CardReviewResponse(
        card_id=card_id,
        next_review_at=schedule.next_review_at,
        interval_days=schedule.interval,
        ease_factor=schedule.ease_factor
    )


# Export endpoints

@router.get("/{deck_id}/export/csv")
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
    
    csv_content = await deck_service.export_deck_csv(deck_id)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{deck.title}.csv"'
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
    
    anki_content = await deck_service.export_deck_anki(deck_id)
    
    return Response(
        content=anki_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{deck.title}.txt"'
        }
    )
