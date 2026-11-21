"""
Generation Service
Builds flashcard decks and quizzes from a processed document with the
built-in generator (local_generator.py). Runs offline; no API key needed.
"""

from __future__ import annotations

import re
from typing import Awaitable, Callable, List, Sequence, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.deck import Card, CardType, Deck, DeckType
from app.models.document import Chunk, Document
from app.models.job import JobLog, ProcessingJob
from app.models.quiz import QuestionType, Quiz, QuizDifficulty, QuizQuestion
from app.schemas.generation import DeckGenerationRequest, QuizGenerationRequest
from app.services.local_generator import ChunkInput, LocalGenerator

logger = structlog.get_logger()

Progress = Callable[[float, str], Awaitable[None]]
VALID_CARD_TYPES = {t.value for t in CardType}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (text or "").lower())).strip()


class GenerationService:
    """Creates decks and quizzes for a ProcessingJob."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #

    async def _load_chunks(self, user_id: int, request) -> Tuple[Document, List[Chunk]]:
        result = await self.db.execute(
            select(Document).where(Document.id == request.document_id, Document.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError("Document not found")

        query = select(Chunk).where(Chunk.document_id == document.id)
        if request.chunk_ids:
            query = query.where(Chunk.id.in_(request.chunk_ids))
        if request.page_range:
            start, end = request.page_range
            query = query.where(Chunk.end_page >= start, Chunk.start_page <= end)
        chunks = list((await self.db.execute(query.order_by(Chunk.chunk_index))).scalars().all())

        if request.topics:
            wanted = [t.lower() for t in request.topics if t.strip()]
            focused = [
                c for c in chunks
                if any(
                    w in (c.heading_context or "").lower()
                    or w in " ".join(c.key_terms or []).lower()
                    or w in c.content.lower()
                    for w in wanted
                )
            ]
            if focused:
                chunks = focused

        if not chunks:
            raise ValueError("This document has no readable text to study from.")
        return document, chunks

    @staticmethod
    def _generator(chunks: Sequence[Chunk], job: ProcessingJob) -> LocalGenerator:
        inputs = [ChunkInput(c.id, c.content, c.start_page, c.end_page, c.heading_context) for c in chunks]
        return LocalGenerator(inputs, seed=job.id or 0)

    def _log(self, job: ProcessingJob, level: str, message: str) -> None:
        self.db.add(JobLog(job_id=job.id, level=level, message=message))

    @staticmethod
    def _dedupe(items: List[dict], key: str, limit: int) -> List[dict]:
        seen: set = set()
        out: List[dict] = []
        for item in items:
            k = _normalize(item[key])
            if k and k not in seen:
                seen.add(k)
                out.append(item)
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------ #
    # Decks
    # ------------------------------------------------------------------ #

    @staticmethod
    def deck_card_types(request: DeckGenerationRequest) -> List[str]:
        if request.card_types:
            return [t.lower() for t in request.card_types]
        types = []
        if request.include_basic or request.include_definitions or request.include_concepts:
            types.append("basic")
        if request.include_cloze:
            types.append("cloze")
        return types or ["basic", "cloze"]

    async def generate_deck(self, user_id: int, request: DeckGenerationRequest, job: ProcessingJob, progress: Progress) -> Deck:
        await progress(10, "Reading document")
        document, chunks = await self._load_chunks(user_id, request)
        count = min(request.max_cards, settings.max_cards_per_document)

        await progress(40, "Finding definitions and key facts")
        generator = self._generator(chunks, job)
        await progress(70, "Writing cards")
        cards = self._dedupe(generator.generate_cards(count + 5, self.deck_card_types(request), request.difficulty), "front", count)
        if not cards:
            raise ValueError(
                "Couldn't find enough definitions or key statements in this document to make cards. "
                "Try a document with more running text."
            )

        await progress(92, "Saving deck")
        name = (request.name or "").strip() or f"{document.title or document.original_filename.rsplit('.', 1)[0]} flashcards"
        deck = Deck(
            user_id=user_id,
            name=name[:255],
            description=f"{len(cards)} cards from {document.original_filename}",
            deck_type=DeckType(request.deck_type) if request.deck_type in {t.value for t in DeckType} else DeckType.MIXED,
            course_id=request.course_id,
            source_document_id=document.id,
            card_count=len(cards),
        )
        self.db.add(deck)
        await self.db.flush()

        for data in cards:
            card_type = data.get("card_type", "basic")
            self.db.add(Card(
                deck_id=deck.id,
                card_type=CardType(card_type) if card_type in VALID_CARD_TYPES else CardType.BASIC,
                front=data["front"],
                back=data["back"],
                extra_explanation=data.get("extra_explanation"),
                cloze_text=data.get("cloze_text"),
                cloze_answer=(data.get("cloze_answer") or None) and data["cloze_answer"][:255],
                difficulty=int(data.get("difficulty", 3)),
                source_pages=data.get("pages"),
                source_snippets=[data["source_quote"]] if data.get("source_quote") else None,
                source_chunk_id=data.get("chunk_id"),
            ))

        job.deck_id = deck.id
        job.result = {"deck_id": deck.id, "card_count": len(cards)}
        self._log(job, "info", f"Created deck with {len(cards)} cards")
        await self.db.flush()
        return deck

    # ------------------------------------------------------------------ #
    # Quizzes
    # ------------------------------------------------------------------ #

    @staticmethod
    def quiz_question_types(request: QuizGenerationRequest) -> List[str]:
        types = []
        if request.include_mcq:
            types.append("mcq")
        if request.include_true_false:
            types.append("true_false")
        if request.include_fill_blank:
            types.append("fill_blank")
        if request.include_short_answer:
            types.append("short_answer")
        return types or ["mcq", "true_false", "fill_blank"]

    async def generate_quiz(self, user_id: int, request: QuizGenerationRequest, job: ProcessingJob, progress: Progress) -> Quiz:
        await progress(10, "Reading document")
        document, chunks = await self._load_chunks(user_id, request)
        types = self.quiz_question_types(request)
        count = min(request.question_count, settings.max_quiz_questions)

        await progress(40, "Finding definitions and key facts")
        generator = self._generator(chunks, job)
        await progress(70, "Writing questions")
        questions = self._dedupe(generator.generate_questions(count + 5, types, request.difficulty), "question_text", count)
        if not questions:
            raise ValueError(
                "Couldn't find enough definitions or key statements in this document to write questions. "
                "Try a document with more running text."
            )

        await progress(92, "Saving quiz")
        name = (request.name or "").strip() or f"{document.title or document.original_filename.rsplit('.', 1)[0]} quiz"
        quiz = Quiz(
            user_id=user_id,
            name=name[:255],
            description=f"{len(questions)} questions from {document.original_filename}",
            difficulty=QuizDifficulty(request.difficulty) if request.difficulty in {d.value for d in QuizDifficulty} else QuizDifficulty.MIXED,
            time_limit_minutes=request.time_limit_minutes,
            shuffle_questions=request.shuffle_questions,
            shuffle_options=request.shuffle_options,
            show_explanations=request.include_explanations,
            question_types=types,
            course_id=request.course_id,
            source_document_id=document.id,
            question_count=len(questions),
        )
        self.db.add(quiz)
        await self.db.flush()

        for order, data in enumerate(questions):
            self.db.add(QuizQuestion(
                quiz_id=quiz.id,
                question_type=QuestionType(data["question_type"]),
                question_text=data["question_text"],
                options=data.get("options"),
                correct_answer=str(data["correct_answer"]),
                explanation=data.get("explanation"),
                difficulty=int(data.get("difficulty", 3)),
                topic=(data.get("topic") or None) and data["topic"][:255],
                source_pages=data.get("pages"),
                source_snippets=[data["source_quote"]] if data.get("source_quote") else None,
                source_chunk_id=data.get("chunk_id"),
                question_order=order,
            ))

        job.quiz_id = quiz.id
        job.result = {"quiz_id": quiz.id, "question_count": len(questions)}
        self._log(job, "info", f"Created quiz with {len(questions)} questions")
        await self.db.flush()
        return quiz
