"""
Generation Tasks
Celery tasks for AI-powered flashcard and quiz generation
"""

from datetime import datetime
import structlog

try:
    from celery import shared_task
except ImportError:
    from app.celery_mock import shared_task

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.job import ProcessingJob, JobStatus

logger = structlog.get_logger()


def get_sync_session() -> Session:
    """Get a synchronous database session for Celery tasks"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3
)
def generate_deck_task(self, job_id: int, request_data: dict) -> dict:
    """
    Generate flashcard deck from document
    This task wraps the async GenerationService for use in Celery
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.database import get_async_database_url
    from app.services.generation import GenerationService
    from app.schemas.generation import DeckGenerationRequest
    
    async def run_generation():
        engine = create_async_engine(get_async_database_url(settings.database_url))
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            # Get job
            result = await session.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return {"error": "Job not found"}
            
            # Update task ID
            job.celery_task_id = self.request.id
            await session.commit()
            
            # Create request object
            request = DeckGenerationRequest(**request_data)
            
            # Run generation
            service = GenerationService(session)
            deck = await service.generate_deck(job.user_id, request, job)
            
            await session.commit()
            
            if deck:
                return {
                    "success": True,
                    "deck_id": deck.id,
                    "card_count": deck.card_count
                }
            else:
                return {"error": "Generation failed"}
    
    return asyncio.run(run_generation())


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3
)
def generate_quiz_task(self, job_id: int, request_data: dict) -> dict:
    """
    Generate quiz from document
    This task wraps the async GenerationService for use in Celery
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.database import get_async_database_url
    from app.services.generation import GenerationService
    from app.schemas.generation import QuizGenerationRequest
    
    async def run_generation():
        engine = create_async_engine(get_async_database_url(settings.database_url))
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            # Get job
            result = await session.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return {"error": "Job not found"}
            
            # Update task ID
            job.celery_task_id = self.request.id
            await session.commit()
            
            # Create request object
            request = QuizGenerationRequest(**request_data)
            
            # Run generation
            service = GenerationService(session)
            quiz = await service.generate_quiz(job.user_id, request, job)
            
            await session.commit()
            
            if quiz:
                return {
                    "success": True,
                    "quiz_id": quiz.id,
                    "question_count": quiz.question_count
                }
            else:
                return {"error": "Generation failed"}
    
    return asyncio.run(run_generation())


@shared_task(bind=True)
def verify_content_task(self, content_type: str, content_id: int) -> dict:
    """
    Verify generated content against source material
    Can be run after manual review to re-verify content
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.database import get_async_database_url
    from app.models.deck import Card
    from app.models.quiz import QuizQuestion
    from app.models.document import Chunk
    from app.services.generation import GenerationService
    
    async def run_verification():
        engine = create_async_engine(get_async_database_url(settings.database_url))
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            service = GenerationService(session)
            
            if content_type == "card":
                result = await session.execute(
                    select(Card).where(Card.id == content_id)
                )
                card = result.scalar_one_or_none()
                
                if not card:
                    return {"error": "Card not found"}
                
                # Get source chunk
                if card.source_chunk_id:
                    chunk_result = await session.execute(
                        select(Chunk).where(Chunk.id == card.source_chunk_id)
                    )
                    chunk = chunk_result.scalar_one_or_none()
                    source_content = chunk.content if chunk else ""
                else:
                    source_content = ""
                
                # Verify
                verification = await service._verify_card(
                    {
                        "front": card.front,
                        "back": card.back,
                        "card_type": card.card_type.value,
                        "source_quote": card.source_snippets[0] if card.source_snippets else ""
                    },
                    source_content
                )
                
                # Update card
                card.needs_review = not verification.get("is_verified", False)
                card.review_reason = "; ".join(verification.get("issues", []))
                card.quality_score = verification.get("confidence", 0.0)
                
                await session.commit()
                
                return verification
            
            elif content_type == "question":
                result = await session.execute(
                    select(QuizQuestion).where(QuizQuestion.id == content_id)
                )
                question = result.scalar_one_or_none()
                
                if not question:
                    return {"error": "Question not found"}
                
                # Get source chunk
                if question.source_chunk_id:
                    chunk_result = await session.execute(
                        select(Chunk).where(Chunk.id == question.source_chunk_id)
                    )
                    chunk = chunk_result.scalar_one_or_none()
                    source_content = chunk.content if chunk else ""
                else:
                    source_content = ""
                
                # Verify
                verification = await service._verify_question(
                    {
                        "question_type": question.question_type.value,
                        "question_text": question.question_text,
                        "options": question.options,
                        "correct_answer": question.correct_answer,
                        "explanation": question.explanation,
                        "source_quote": question.source_snippets[0] if question.source_snippets else ""
                    },
                    source_content
                )
                
                # Update question
                question.needs_review = not verification.get("is_verified", False)
                question.review_reason = "; ".join(verification.get("issues", []))
                
                await session.commit()
                
                return verification
            
            return {"error": "Invalid content type"}
    
    return asyncio.run(run_verification())
