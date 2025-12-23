"""
Generation Service
AI-powered flashcard and quiz generation with verification
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, List, Any
import structlog

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.document import Document, Chunk
from app.models.deck import Deck, Card, DeckType, CardType
from app.models.quiz import Quiz, QuizQuestion, QuestionType, QuizDifficulty
from app.models.job import ProcessingJob, JobStatus, JobType, JobLog
from app.services.prompts import (
    EXTRACT_FACTS_PROMPT,
    GENERATE_FLASHCARDS_PROMPT,
    GENERATE_QUIZ_PROMPT,
    VERIFY_CARD_PROMPT,
    VERIFY_QUESTION_PROMPT,
    CALIBRATE_DIFFICULTY_PROMPT
)
from app.schemas.generation import DeckGenerationRequest, QuizGenerationRequest

logger = structlog.get_logger()


class GenerationService:
    """Service for AI-powered content generation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def _call_openai(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Optional[dict]:
        """Call OpenAI API and parse JSON response"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content creator. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response as JSON", error=str(e))
            return None
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e))
            return None
    
    async def _extract_facts_from_chunk(
        self,
        chunk: Chunk
    ) -> Optional[dict]:
        """Extract facts from a single chunk"""
        prompt = EXTRACT_FACTS_PROMPT.format(
            content=chunk.content,
            heading_context=chunk.heading_context or "None",
            page_range=f"{chunk.start_page}-{chunk.end_page}",
            content_type=chunk.content_type
        )
        
        return await self._call_openai(prompt, temperature=0.3)
    
    async def _generate_flashcards_from_facts(
        self,
        facts: List[dict],
        request: DeckGenerationRequest
    ) -> Optional[dict]:
        """Generate flashcards from extracted facts"""
        # Determine card types to include
        card_types = []
        if request.include_basic:
            card_types.append("basic")
        if request.include_definitions:
            card_types.append("definition")
        if request.include_concepts:
            card_types.append("concept")
        if request.include_processes:
            card_types.append("process")
        if request.include_formulas:
            card_types.append("formula")
        if request.include_cloze:
            card_types.append("cloze")
        if request.include_eli5:
            card_types.append("eli5")
        
        prompt = GENERATE_FLASHCARDS_PROMPT.format(
            facts_json=json.dumps(facts, indent=2),
            difficulty=request.difficulty,
            include_eli5=request.include_eli5,
            include_examples=request.include_examples,
            include_mnemonics=request.include_mnemonics,
            card_types=", ".join(card_types)
        )
        
        return await self._call_openai(prompt, max_tokens=8000, temperature=0.7)
    
    async def _generate_quiz_from_facts(
        self,
        facts: List[dict],
        request: QuizGenerationRequest
    ) -> Optional[dict]:
        """Generate quiz questions from extracted facts"""
        # Determine question types
        question_types = []
        if request.include_mcq:
            question_types.append("mcq")
        if request.include_multi_select:
            question_types.append("multi_select")
        if request.include_true_false:
            question_types.append("true_false")
        if request.include_short_answer:
            question_types.append("short_answer")
        if request.include_fill_blank:
            question_types.append("fill_blank")
        if request.include_matching:
            question_types.append("matching")
        
        prompt = GENERATE_QUIZ_PROMPT.format(
            facts_json=json.dumps(facts, indent=2),
            question_count=request.question_count,
            difficulty=request.difficulty,
            question_types=", ".join(question_types)
        )
        
        return await self._call_openai(prompt, max_tokens=8000, temperature=0.7)
    
    async def _verify_card(
        self,
        card_data: dict,
        source_content: str
    ) -> dict:
        """Verify a single flashcard against source content"""
        prompt = VERIFY_CARD_PROMPT.format(
            front=card_data.get("front", ""),
            back=card_data.get("back", ""),
            card_type=card_data.get("card_type", "basic"),
            source_content=source_content[:2000],
            source_quote=card_data.get("source_quote", "")
        )
        
        result = await self._call_openai(prompt, max_tokens=500, temperature=0.2)
        
        if result:
            return result
        
        # Default to needs review if verification fails
        return {
            "is_verified": False,
            "confidence": 0.0,
            "issues": ["Verification failed"],
            "suggested_fix": None,
            "verification_notes": "Could not complete verification"
        }
    
    async def _verify_question(
        self,
        question_data: dict,
        source_content: str
    ) -> dict:
        """Verify a single quiz question against source content"""
        prompt = VERIFY_QUESTION_PROMPT.format(
            question_type=question_data.get("question_type", "mcq"),
            question_text=question_data.get("question_text", ""),
            options=json.dumps(question_data.get("options", [])),
            correct_answer=question_data.get("correct_answer", ""),
            explanation=question_data.get("explanation", ""),
            source_content=source_content[:2000],
            source_quote=question_data.get("source_quote", "")
        )
        
        result = await self._call_openai(prompt, max_tokens=500, temperature=0.2)
        
        if result:
            return result
        
        return {
            "is_verified": False,
            "confidence": 0.0,
            "issues": ["Verification failed"],
            "suggested_fix": None,
            "verification_notes": "Could not complete verification"
        }
    
    async def generate_deck(
        self,
        user_id: int,
        request: DeckGenerationRequest,
        job: ProcessingJob
    ) -> Optional[Deck]:
        """Generate a complete flashcard deck from a document"""
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.current_step = "Loading document"
            await self.db.flush()
            
            # Get document and chunks
            result = await self.db.execute(
                select(Document).where(
                    Document.id == request.document_id,
                    Document.user_id == user_id
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError("Document not found")
            
            # Get chunks
            chunk_query = select(Chunk).where(Chunk.document_id == document.id)
            
            if request.chunk_ids:
                chunk_query = chunk_query.where(Chunk.id.in_(request.chunk_ids))
            
            if request.page_range:
                start, end = request.page_range
                chunk_query = chunk_query.where(
                    Chunk.start_page >= start,
                    Chunk.end_page <= end
                )
            
            chunk_query = chunk_query.order_by(Chunk.chunk_index).limit(
                settings.max_chunks_per_generation
            )
            
            result = await self.db.execute(chunk_query)
            chunks = list(result.scalars().all())
            
            if not chunks:
                raise ValueError("No chunks found for generation")
            
            # Log progress
            await self._log_job(job, "info", f"Processing {len(chunks)} chunks")
            job.total_steps = len(chunks) * 2 + 2  # Extract + Generate + Verify + Create
            
            # Step 1: Extract facts from all chunks
            job.current_step = "Extracting facts"
            await self.db.flush()
            
            all_facts = []
            chunk_content_map = {}
            
            for i, chunk in enumerate(chunks):
                facts_result = await self._extract_facts_from_chunk(chunk)
                
                if facts_result and "facts" in facts_result:
                    for fact in facts_result["facts"]:
                        fact["chunk_id"] = chunk.id
                        fact["pages"] = [chunk.start_page, chunk.end_page]
                    all_facts.extend(facts_result["facts"])
                    chunk_content_map[chunk.id] = chunk.content
                
                job.completed_steps += 1
                job.progress = (job.completed_steps / job.total_steps) * 100
                await self.db.flush()
            
            if not all_facts:
                raise ValueError("Could not extract any facts from document")
            
            await self._log_job(job, "info", f"Extracted {len(all_facts)} facts")
            
            # Step 2: Generate flashcards
            job.current_step = "Generating flashcards"
            await self.db.flush()
            
            # Process in batches to respect max cards
            max_facts_per_batch = 20
            all_cards = []
            
            for i in range(0, len(all_facts), max_facts_per_batch):
                batch_facts = all_facts[i:i + max_facts_per_batch]
                cards_result = await self._generate_flashcards_from_facts(batch_facts, request)
                
                if cards_result and "cards" in cards_result:
                    for card in cards_result["cards"]:
                        # Link back to chunk
                        fact_idx = card.get("source_fact_index", 0)
                        if fact_idx < len(batch_facts):
                            card["chunk_id"] = batch_facts[fact_idx].get("chunk_id")
                            card["pages"] = batch_facts[fact_idx].get("pages", [])
                    all_cards.extend(cards_result["cards"])
                
                if len(all_cards) >= request.max_cards:
                    all_cards = all_cards[:request.max_cards]
                    break
                
                job.completed_steps += 1
                job.progress = (job.completed_steps / job.total_steps) * 100
                await self.db.flush()
            
            if not all_cards:
                raise ValueError("Could not generate any flashcards")
            
            await self._log_job(job, "info", f"Generated {len(all_cards)} cards")
            
            # Step 3: Verify cards
            job.current_step = "Verifying cards"
            await self.db.flush()
            
            verified_cards = []
            needs_review_cards = []
            
            for card in all_cards:
                chunk_id = card.get("chunk_id")
                source_content = chunk_content_map.get(chunk_id, "")
                
                verification = await self._verify_card(card, source_content)
                
                if verification.get("is_verified", False) and verification.get("confidence", 0) >= 0.7:
                    card["needs_review"] = False
                    verified_cards.append(card)
                else:
                    card["needs_review"] = True
                    card["review_reason"] = "; ".join(verification.get("issues", ["Unverified"]))
                    needs_review_cards.append(card)
            
            final_cards = verified_cards + needs_review_cards
            
            job.completed_steps += 1
            job.progress = (job.completed_steps / job.total_steps) * 100
            
            await self._log_job(
                job, "info",
                f"Verified {len(verified_cards)} cards, {len(needs_review_cards)} need review"
            )
            
            # Step 4: Create deck and cards
            job.current_step = "Creating deck"
            await self.db.flush()
            
            # Create deck
            deck_name = request.name or f"Deck from {document.title}"
            deck = Deck(
                user_id=user_id,
                name=deck_name,
                description=f"Generated from {document.original_filename}",
                deck_type=DeckType(request.deck_type) if request.deck_type else DeckType.MIXED,
                course_id=request.course_id,
                source_document_id=document.id,
                card_count=0
            )
            
            self.db.add(deck)
            await self.db.flush()
            
            # Create cards
            for card_data in final_cards:
                card = Card(
                    deck_id=deck.id,
                    card_type=CardType(card_data.get("card_type", "basic")),
                    front=card_data.get("front", ""),
                    back=card_data.get("back", ""),
                    extra_explanation=card_data.get("extra_explanation"),
                    example=card_data.get("example"),
                    mnemonic=card_data.get("mnemonic"),
                    cloze_text=card_data.get("cloze_text"),
                    cloze_answer=card_data.get("cloze_answer"),
                    difficulty=card_data.get("difficulty", 3),
                    source_pages=card_data.get("pages"),
                    source_snippets=[card_data.get("source_quote")] if card_data.get("source_quote") else None,
                    source_chunk_id=card_data.get("chunk_id"),
                    needs_review=card_data.get("needs_review", False),
                    review_reason=card_data.get("review_reason")
                )
                self.db.add(card)
                deck.card_count += 1
            
            # Update job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.current_step = "Completed"
            job.completed_steps = job.total_steps
            job.progress = 100
            job.deck_id = deck.id
            job.result = {
                "deck_id": deck.id,
                "card_count": deck.card_count,
                "verified_count": len(verified_cards),
                "needs_review_count": len(needs_review_cards)
            }
            
            await self.db.flush()
            await self.db.refresh(deck)
            
            await self._log_job(job, "info", f"Created deck with {deck.card_count} cards")
            
            return deck
        
        except Exception as e:
            logger.error("Deck generation failed", error=str(e))
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self._log_job(job, "error", f"Generation failed: {str(e)}")
            await self.db.flush()
            return None
    
    async def generate_quiz(
        self,
        user_id: int,
        request: QuizGenerationRequest,
        job: ProcessingJob
    ) -> Optional[Quiz]:
        """Generate a quiz from a document"""
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.current_step = "Loading document"
            await self.db.flush()
            
            # Get document and chunks
            result = await self.db.execute(
                select(Document).where(
                    Document.id == request.document_id,
                    Document.user_id == user_id
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError("Document not found")
            
            # Get chunks
            chunk_query = select(Chunk).where(Chunk.document_id == document.id)
            
            if request.chunk_ids:
                chunk_query = chunk_query.where(Chunk.id.in_(request.chunk_ids))
            
            if request.page_range:
                start, end = request.page_range
                chunk_query = chunk_query.where(
                    Chunk.start_page >= start,
                    Chunk.end_page <= end
                )
            
            chunk_query = chunk_query.order_by(Chunk.chunk_index).limit(
                settings.max_chunks_per_generation
            )
            
            result = await self.db.execute(chunk_query)
            chunks = list(result.scalars().all())
            
            if not chunks:
                raise ValueError("No chunks found for generation")
            
            await self._log_job(job, "info", f"Processing {len(chunks)} chunks")
            job.total_steps = 4
            
            # Step 1: Extract facts
            job.current_step = "Extracting facts"
            await self.db.flush()
            
            all_facts = []
            chunk_content_map = {}
            
            for chunk in chunks:
                facts_result = await self._extract_facts_from_chunk(chunk)
                
                if facts_result and "facts" in facts_result:
                    for fact in facts_result["facts"]:
                        fact["chunk_id"] = chunk.id
                        fact["pages"] = [chunk.start_page, chunk.end_page]
                    all_facts.extend(facts_result["facts"])
                    chunk_content_map[chunk.id] = chunk.content
            
            if not all_facts:
                raise ValueError("Could not extract any facts from document")
            
            job.completed_steps = 1
            job.progress = 25
            await self._log_job(job, "info", f"Extracted {len(all_facts)} facts")
            
            # Step 2: Generate questions
            job.current_step = "Generating questions"
            await self.db.flush()
            
            questions_result = await self._generate_quiz_from_facts(all_facts, request)
            
            if not questions_result or "questions" not in questions_result:
                raise ValueError("Could not generate quiz questions")
            
            all_questions = questions_result["questions"]
            
            # Link back to chunks
            for q in all_questions:
                fact_idx = q.get("source_fact_index", 0)
                if fact_idx < len(all_facts):
                    q["chunk_id"] = all_facts[fact_idx].get("chunk_id")
                    q["pages"] = all_facts[fact_idx].get("pages", [])
            
            job.completed_steps = 2
            job.progress = 50
            await self._log_job(job, "info", f"Generated {len(all_questions)} questions")
            
            # Step 3: Verify questions
            job.current_step = "Verifying questions"
            await self.db.flush()
            
            verified_questions = []
            needs_review_questions = []
            
            for q in all_questions[:request.question_count]:
                chunk_id = q.get("chunk_id")
                source_content = chunk_content_map.get(chunk_id, "")
                
                verification = await self._verify_question(q, source_content)
                
                if verification.get("is_verified", False) and verification.get("confidence", 0) >= 0.7:
                    q["needs_review"] = False
                    verified_questions.append(q)
                else:
                    q["needs_review"] = True
                    q["review_reason"] = "; ".join(verification.get("issues", ["Unverified"]))
                    needs_review_questions.append(q)
            
            final_questions = verified_questions + needs_review_questions
            
            job.completed_steps = 3
            job.progress = 75
            await self._log_job(
                job, "info",
                f"Verified {len(verified_questions)} questions, {len(needs_review_questions)} need review"
            )
            
            # Step 4: Create quiz
            job.current_step = "Creating quiz"
            await self.db.flush()
            
            quiz_name = request.name or f"Quiz from {document.title}"
            quiz = Quiz(
                user_id=user_id,
                name=quiz_name,
                description=f"Generated from {document.original_filename}",
                difficulty=QuizDifficulty(request.difficulty) if request.difficulty else QuizDifficulty.MIXED,
                time_limit_minutes=request.time_limit_minutes,
                shuffle_questions=request.shuffle_questions,
                shuffle_options=request.shuffle_options,
                show_explanations=request.include_explanations,
                course_id=request.course_id,
                source_document_id=document.id,
                question_count=0
            )
            
            self.db.add(quiz)
            await self.db.flush()
            
            # Create questions
            for idx, q_data in enumerate(final_questions):
                correct_answer = q_data.get("correct_answer", "")
                if isinstance(correct_answer, (list, dict)):
                    correct_answer = json.dumps(correct_answer)
                
                question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_type=QuestionType(q_data.get("question_type", "mcq")),
                    question_text=q_data.get("question_text", ""),
                    options=q_data.get("options"),
                    correct_answer=correct_answer,
                    explanation=q_data.get("explanation"),
                    difficulty=q_data.get("difficulty", 3),
                    topic=q_data.get("topic"),
                    source_pages=q_data.get("pages"),
                    source_snippets=[q_data.get("source_quote")] if q_data.get("source_quote") else None,
                    source_chunk_id=q_data.get("chunk_id"),
                    question_order=idx,
                    needs_review=q_data.get("needs_review", False),
                    review_reason=q_data.get("review_reason")
                )
                self.db.add(question)
                quiz.question_count += 1
            
            # Update job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.current_step = "Completed"
            job.completed_steps = job.total_steps
            job.progress = 100
            job.quiz_id = quiz.id
            job.result = {
                "quiz_id": quiz.id,
                "question_count": quiz.question_count,
                "verified_count": len(verified_questions),
                "needs_review_count": len(needs_review_questions)
            }
            
            await self.db.flush()
            await self.db.refresh(quiz)
            
            await self._log_job(job, "info", f"Created quiz with {quiz.question_count} questions")
            
            return quiz
        
        except Exception as e:
            logger.error("Quiz generation failed", error=str(e))
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self._log_job(job, "error", f"Generation failed: {str(e)}")
            await self.db.flush()
            return None
    
    async def _log_job(
        self,
        job: ProcessingJob,
        level: str,
        message: str,
        details: Optional[dict] = None
    ) -> None:
        """Add a log entry to a job"""
        log = JobLog(
            job_id=job.id,
            level=level,
            message=message,
            details=details
        )
        self.db.add(log)
        await self.db.flush()
