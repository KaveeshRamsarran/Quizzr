"""
Deck Service
Handles deck and card management
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.deck import Deck, Card, DeckType, CardType
from app.models.tag import Tag, CardTag
from app.models.spaced_repetition import SpacedRepetitionSchedule
from app.schemas.deck import DeckCreate, DeckUpdate, CardCreate, CardUpdate


class DeckService:
    """Service for deck and card management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_deck(
        self,
        user_id: int,
        deck_data: DeckCreate,
        source_document_id: Optional[int] = None
    ) -> Deck:
        """Create a new deck"""
        deck = Deck(
            user_id=user_id,
            name=deck_data.name,
            description=deck_data.description,
            deck_type=DeckType(deck_data.deck_type) if deck_data.deck_type else DeckType.MIXED,
            course_id=deck_data.course_id,
            source_document_id=source_document_id,
            color=deck_data.color,
            is_public=deck_data.is_public,
            card_count=0,
            mastered_count=0
        )
        
        self.db.add(deck)
        await self.db.flush()
        await self.db.refresh(deck)
        return deck
    
    async def get_deck(
        self,
        deck_id: int,
        user_id: int,
        include_cards: bool = False
    ) -> Optional[Deck]:
        """Get a deck by ID"""
        query = select(Deck).where(
            Deck.id == deck_id,
            Deck.user_id == user_id
        )
        
        if include_cards:
            query = query.options(selectinload(Deck.cards))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_decks(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Deck], int]:
        """Get decks for a user"""
        query = select(Deck).where(Deck.user_id == user_id)
        count_query = select(func.count(Deck.id)).where(Deck.user_id == user_id)
        
        if course_id is not None:
            query = query.where(Deck.course_id == course_id)
            count_query = count_query.where(Deck.course_id == course_id)
        
        # Get total
        total = await self.db.execute(count_query)
        total_count = total.scalar()
        
        # Get decks
        query = query.order_by(Deck.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        decks = list(result.scalars().all())
        
        return decks, total_count
    
    async def update_deck(
        self,
        deck_id: int,
        user_id: int,
        deck_data: DeckUpdate
    ) -> Optional[Deck]:
        """Update a deck"""
        deck = await self.get_deck(deck_id, user_id)
        if not deck:
            return None
        
        update_dict = deck_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(deck, field, value)
        
        deck.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(deck)
        return deck
    
    async def delete_deck(self, deck_id: int, user_id: int) -> bool:
        """Delete a deck"""
        deck = await self.get_deck(deck_id, user_id)
        if not deck:
            return False
        
        await self.db.delete(deck)
        await self.db.flush()
        return True
    
    async def create_card(
        self,
        deck_id: int,
        user_id: int,
        card_data: CardCreate
    ) -> Optional[Card]:
        """Create a new card in a deck"""
        # Verify deck ownership
        deck = await self.get_deck(deck_id, user_id)
        if not deck:
            return None
        
        card = Card(
            deck_id=deck_id,
            card_type=CardType(card_data.card_type) if card_data.card_type else CardType.BASIC,
            front=card_data.front,
            back=card_data.back,
            extra_explanation=card_data.extra_explanation,
            example=card_data.example,
            mnemonic=card_data.mnemonic,
            cloze_text=card_data.cloze_text,
            cloze_answer=card_data.cloze_answer,
            difficulty=card_data.difficulty,
            source_pages=card_data.source_pages,
            source_snippets=card_data.source_snippets
        )
        
        self.db.add(card)
        
        # Update deck card count
        deck.card_count += 1
        deck.updated_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Add tags
        if card_data.tags:
            await self._add_card_tags(card.id, card_data.tags)
        
        await self.db.refresh(card)
        return card
    
    async def create_cards_bulk(
        self,
        deck_id: int,
        user_id: int,
        cards_data: List[CardCreate]
    ) -> List[Card]:
        """Create multiple cards in a deck"""
        deck = await self.get_deck(deck_id, user_id)
        if not deck:
            return []
        
        cards = []
        for card_data in cards_data:
            card = Card(
                deck_id=deck_id,
                card_type=CardType(card_data.card_type) if card_data.card_type else CardType.BASIC,
                front=card_data.front,
                back=card_data.back,
                extra_explanation=card_data.extra_explanation,
                example=card_data.example,
                mnemonic=card_data.mnemonic,
                cloze_text=card_data.cloze_text,
                cloze_answer=card_data.cloze_answer,
                difficulty=card_data.difficulty,
                source_pages=card_data.source_pages,
                source_snippets=card_data.source_snippets
            )
            self.db.add(card)
            cards.append(card)
        
        # Update deck
        deck.card_count += len(cards)
        deck.updated_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Add tags for each card
        for card, card_data in zip(cards, cards_data):
            if card_data.tags:
                await self._add_card_tags(card.id, card_data.tags)
        
        return cards
    
    async def get_card(
        self,
        card_id: int,
        user_id: int
    ) -> Optional[Card]:
        """Get a card by ID"""
        result = await self.db.execute(
            select(Card)
            .join(Deck)
            .where(Card.id == card_id, Deck.user_id == user_id)
            .options(selectinload(Card.tags))
        )
        return result.scalar_one_or_none()
    
    async def get_deck_cards(
        self,
        deck_id: int,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Card]:
        """Get cards in a deck"""
        deck = await self.get_deck(deck_id, user_id)
        if not deck:
            return []
        
        result = await self.db.execute(
            select(Card)
            .where(Card.deck_id == deck_id)
            .options(selectinload(Card.tags))
            .order_by(Card.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def update_card(
        self,
        card_id: int,
        user_id: int,
        card_data: CardUpdate
    ) -> Optional[Card]:
        """Update a card"""
        card = await self.get_card(card_id, user_id)
        if not card:
            return None
        
        update_dict = card_data.model_dump(exclude_unset=True, exclude={"tags"})
        for field, value in update_dict.items():
            setattr(card, field, value)
        
        card.updated_at = datetime.utcnow()
        
        # Update tags if provided
        if card_data.tags is not None:
            # Remove existing tags
            await self.db.execute(
                CardTag.__table__.delete().where(CardTag.card_id == card_id)
            )
            # Add new tags
            await self._add_card_tags(card_id, card_data.tags)
        
        await self.db.flush()
        await self.db.refresh(card)
        return card
    
    async def delete_card(self, card_id: int, user_id: int) -> bool:
        """Delete a card"""
        card = await self.get_card(card_id, user_id)
        if not card:
            return False
        
        # Update deck count
        result = await self.db.execute(
            select(Deck).where(Deck.id == card.deck_id)
        )
        deck = result.scalar_one_or_none()
        if deck:
            deck.card_count = max(0, deck.card_count - 1)
            if card.is_mastered:
                deck.mastered_count = max(0, deck.mastered_count - 1)
        
        await self.db.delete(card)
        await self.db.flush()
        return True
    
    async def _add_card_tags(self, card_id: int, tag_names: List[str]) -> None:
        """Add tags to a card, creating tags if needed"""
        for tag_name in tag_names:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            
            # Get or create tag
            result = await self.db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name, usage_count=0)
                self.db.add(tag)
                await self.db.flush()
            
            # Create card-tag relationship
            card_tag = CardTag(card_id=card_id, tag_id=tag.id)
            self.db.add(card_tag)
            
            # Increment usage count
            tag.usage_count += 1
        
        await self.db.flush()
    
    async def get_deck_with_schedule(
        self,
        deck_id: int,
        user_id: int
    ) -> Optional[dict]:
        """Get deck with card schedule info"""
        deck = await self.get_deck(deck_id, user_id, include_cards=True)
        if not deck:
            return None
        
        now = datetime.utcnow()
        
        # Get schedules for all cards
        result = await self.db.execute(
            select(SpacedRepetitionSchedule)
            .where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.card_id.in_([c.id for c in deck.cards])
            )
        )
        schedules = {s.card_id: s for s in result.scalars().all()}
        
        # Calculate stats
        due_count = 0
        new_count = 0
        
        for card in deck.cards:
            if card.is_suspended:
                continue
            
            schedule = schedules.get(card.id)
            if not schedule:
                new_count += 1
            elif schedule.next_review <= now:
                due_count += 1
        
        return {
            "deck": deck,
            "due_count": due_count,
            "new_count": new_count,
            "schedules": schedules
        }
    
    async def search_cards(
        self,
        user_id: int,
        query: str,
        deck_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Card]:
        """Search cards by content"""
        search_query = (
            select(Card)
            .join(Deck)
            .where(
                Deck.user_id == user_id,
                (Card.front.ilike(f"%{query}%") | Card.back.ilike(f"%{query}%"))
            )
        )
        
        if deck_id:
            search_query = search_query.where(Card.deck_id == deck_id)
        
        search_query = search_query.limit(limit)
        
        result = await self.db.execute(search_query)
        return list(result.scalars().all())
    
    async def export_deck_csv(
        self,
        deck_id: int,
        user_id: int
    ) -> Optional[str]:
        """Export deck to CSV format"""
        cards = await self.get_deck_cards(deck_id, user_id, limit=10000)
        if not cards:
            return None
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Front", "Back", "Type", "Difficulty", "Extra", "Tags"])
        
        for card in cards:
            tags = ",".join([t.tag.name for t in card.tags]) if card.tags else ""
            writer.writerow([
                card.front,
                card.back,
                card.card_type.value,
                card.difficulty,
                card.extra_explanation or "",
                tags
            ])
        
        return output.getvalue()
    
    async def export_deck_anki(
        self,
        deck_id: int,
        user_id: int
    ) -> Optional[str]:
        """Export deck to Anki-compatible TSV format"""
        cards = await self.get_deck_cards(deck_id, user_id, limit=10000)
        if not cards:
            return None
        
        lines = []
        for card in cards:
            # Anki format: front\tback\ttags
            tags = " ".join([t.tag.name for t in card.tags]) if card.tags else ""
            front = card.front.replace("\t", " ").replace("\n", "<br>")
            back = card.back.replace("\t", " ").replace("\n", "<br>")
            lines.append(f"{front}\t{back}\t{tags}")
        
        return "\n".join(lines)
