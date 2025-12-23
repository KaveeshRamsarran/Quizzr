"""
Quiz Service
Handles quiz management, attempts, and scoring
"""

from datetime import datetime
from typing import Optional, List, Any
import random
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.models.quiz import (
    Quiz, QuizQuestion, QuestionType, QuizDifficulty,
    QuizAttempt, QuizAttemptAnswer
)
from app.models.tag import Tag, QuestionTag
from app.schemas.quiz import QuizCreate, QuizUpdate


class QuizService:
    """Service for quiz management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_quiz(
        self,
        user_id: int,
        quiz_data: QuizCreate,
        source_document_id: Optional[int] = None
    ) -> Quiz:
        """Create a new quiz"""
        quiz = Quiz(
            user_id=user_id,
            name=quiz_data.name,
            description=quiz_data.description,
            difficulty=QuizDifficulty(quiz_data.difficulty) if quiz_data.difficulty else QuizDifficulty.MIXED,
            time_limit_minutes=quiz_data.time_limit_minutes,
            shuffle_questions=quiz_data.shuffle_questions,
            shuffle_options=quiz_data.shuffle_options,
            show_explanations=quiz_data.show_explanations,
            question_types=quiz_data.question_types,
            course_id=quiz_data.course_id,
            source_document_id=source_document_id,
            question_count=0
        )
        
        self.db.add(quiz)
        await self.db.flush()
        await self.db.refresh(quiz)
        return quiz
    
    async def get_quiz(
        self,
        quiz_id: int,
        user_id: int,
        include_questions: bool = False
    ) -> Optional[Quiz]:
        """Get a quiz by ID"""
        query = select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id)
        
        if include_questions:
            query = query.options(selectinload(Quiz.questions))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_quizzes(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Quiz], int]:
        """Get quizzes for a user"""
        query = select(Quiz).where(Quiz.user_id == user_id)
        count_query = select(func.count(Quiz.id)).where(Quiz.user_id == user_id)
        
        if course_id is not None:
            query = query.where(Quiz.course_id == course_id)
            count_query = count_query.where(Quiz.course_id == course_id)
        
        total = await self.db.execute(count_query)
        total_count = total.scalar()
        
        query = query.order_by(Quiz.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        quizzes = list(result.scalars().all())
        
        return quizzes, total_count
    
    async def update_quiz(
        self,
        quiz_id: int,
        user_id: int,
        quiz_data: QuizUpdate
    ) -> Optional[Quiz]:
        """Update a quiz"""
        quiz = await self.get_quiz(quiz_id, user_id)
        if not quiz:
            return None
        
        update_dict = quiz_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(quiz, field, value)
        
        quiz.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(quiz)
        return quiz
    
    async def delete_quiz(self, quiz_id: int, user_id: int) -> bool:
        """Delete a quiz"""
        quiz = await self.get_quiz(quiz_id, user_id)
        if not quiz:
            return False
        
        await self.db.delete(quiz)
        await self.db.flush()
        return True
    
    async def add_question(
        self,
        quiz_id: int,
        user_id: int,
        question_type: str,
        question_text: str,
        correct_answer: Any,
        options: Optional[List[dict]] = None,
        explanation: Optional[str] = None,
        difficulty: int = 3,
        points: int = 1,
        topic: Optional[str] = None,
        source_pages: Optional[List[int]] = None,
        source_snippets: Optional[List[str]] = None,
        source_chunk_id: Optional[int] = None
    ) -> Optional[QuizQuestion]:
        """Add a question to a quiz"""
        quiz = await self.get_quiz(quiz_id, user_id)
        if not quiz:
            return None
        
        # Convert answer to string for storage
        if isinstance(correct_answer, (list, dict)):
            answer_str = json.dumps(correct_answer)
        else:
            answer_str = str(correct_answer)
        
        question = QuizQuestion(
            quiz_id=quiz_id,
            question_type=QuestionType(question_type),
            question_text=question_text,
            options=options,
            correct_answer=answer_str,
            explanation=explanation,
            difficulty=difficulty,
            points=points,
            topic=topic,
            source_pages=source_pages,
            source_snippets=source_snippets,
            source_chunk_id=source_chunk_id,
            question_order=quiz.question_count
        )
        
        self.db.add(question)
        
        # Update quiz
        quiz.question_count += 1
        quiz.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(question)
        return question
    
    async def add_questions_bulk(
        self,
        quiz_id: int,
        user_id: int,
        questions_data: List[dict]
    ) -> List[QuizQuestion]:
        """Add multiple questions to a quiz"""
        quiz = await self.get_quiz(quiz_id, user_id)
        if not quiz:
            return []
        
        questions = []
        for idx, q_data in enumerate(questions_data):
            answer = q_data.get("correct_answer")
            if isinstance(answer, (list, dict)):
                answer_str = json.dumps(answer)
            else:
                answer_str = str(answer)
            
            question = QuizQuestion(
                quiz_id=quiz_id,
                question_type=QuestionType(q_data.get("question_type", "mcq")),
                question_text=q_data["question_text"],
                options=q_data.get("options"),
                correct_answer=answer_str,
                explanation=q_data.get("explanation"),
                difficulty=q_data.get("difficulty", 3),
                points=q_data.get("points", 1),
                topic=q_data.get("topic"),
                source_pages=q_data.get("source_pages"),
                source_snippets=q_data.get("source_snippets"),
                source_chunk_id=q_data.get("source_chunk_id"),
                question_order=quiz.question_count + idx,
                needs_review=q_data.get("needs_review", False),
                review_reason=q_data.get("review_reason")
            )
            self.db.add(question)
            questions.append(question)
        
        quiz.question_count += len(questions)
        quiz.updated_at = datetime.utcnow()
        
        await self.db.flush()
        return questions
    
    async def start_attempt(
        self,
        quiz_id: int,
        user_id: int
    ) -> Optional[QuizAttempt]:
        """Start a new quiz attempt"""
        quiz = await self.get_quiz(quiz_id, user_id, include_questions=True)
        if not quiz or not quiz.questions:
            return None
        
        # Calculate total points
        points_possible = sum(q.points for q in quiz.questions)
        
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            is_completed=False,
            points_possible=points_possible,
            time_started=datetime.utcnow()
        )
        
        self.db.add(attempt)
        await self.db.flush()
        await self.db.refresh(attempt)
        return attempt
    
    async def get_attempt(
        self,
        attempt_id: int,
        user_id: int
    ) -> Optional[QuizAttempt]:
        """Get an attempt by ID"""
        result = await self.db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
            .options(selectinload(QuizAttempt.answers))
        )
        return result.scalar_one_or_none()
    
    async def get_attempt_questions(
        self,
        attempt_id: int,
        user_id: int
    ) -> List[dict]:
        """Get questions for an attempt (with shuffling if enabled)"""
        attempt = await self.get_attempt(attempt_id, user_id)
        if not attempt:
            return []
        
        quiz = await self.get_quiz(attempt.quiz_id, user_id, include_questions=True)
        if not quiz:
            return []
        
        questions = list(quiz.questions)
        
        # Shuffle questions if enabled
        if quiz.shuffle_questions:
            random.shuffle(questions)
        
        # Get already answered question IDs
        answered_ids = {a.question_id for a in attempt.answers}
        
        result = []
        for q in questions:
            q_dict = {
                "id": q.id,
                "question_type": q.question_type.value,
                "question_text": q.question_text,
                "options": q.options,
                "difficulty": q.difficulty,
                "points": q.points,
                "topic": q.topic,
                "is_answered": q.id in answered_ids
            }
            
            # Shuffle options if enabled and MCQ/multi-select
            if quiz.shuffle_options and q.options:
                shuffled_options = list(q.options)
                random.shuffle(shuffled_options)
                q_dict["options"] = shuffled_options
            
            result.append(q_dict)
        
        return result
    
    async def submit_answer(
        self,
        attempt_id: int,
        user_id: int,
        question_id: int,
        answer: Any,
        time_spent_seconds: Optional[int] = None
    ) -> Optional[dict]:
        """Submit an answer for a question"""
        attempt = await self.get_attempt(attempt_id, user_id)
        if not attempt or attempt.is_completed:
            return None
        
        # Get question
        result = await self.db.execute(
            select(QuizQuestion).where(
                QuizQuestion.id == question_id,
                QuizQuestion.quiz_id == attempt.quiz_id
            )
        )
        question = result.scalar_one_or_none()
        if not question:
            return None
        
        # Check if already answered
        existing = await self.db.execute(
            select(QuizAttemptAnswer).where(
                QuizAttemptAnswer.attempt_id == attempt_id,
                QuizAttemptAnswer.question_id == question_id
            )
        )
        if existing.scalar_one_or_none():
            return None  # Already answered
        
        # Check answer
        is_correct = self._check_answer(question, answer)
        points = question.points if is_correct else 0
        
        # Convert answer to string
        if isinstance(answer, (list, dict)):
            answer_str = json.dumps(answer)
        else:
            answer_str = str(answer)
        
        # Record answer
        attempt_answer = QuizAttemptAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            user_answer=answer_str,
            is_correct=is_correct,
            points_earned=points,
            time_spent_seconds=time_spent_seconds
        )
        
        self.db.add(attempt_answer)
        
        # Update attempt stats
        attempt.points_earned += points
        if is_correct:
            attempt.correct_count += 1
        else:
            attempt.incorrect_count += 1
        
        # Update question stats
        question.times_answered += 1
        if is_correct:
            question.times_correct += 1
        
        await self.db.flush()
        
        # Get quiz to check if explanations should be shown
        quiz = await self.get_quiz(attempt.quiz_id, user_id)
        
        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "points_earned": points,
            "correct_answer": question.correct_answer if quiz.show_explanations else None,
            "explanation": question.explanation if quiz.show_explanations else None
        }
    
    def _check_answer(self, question: QuizQuestion, user_answer: Any) -> bool:
        """Check if answer is correct"""
        correct = question.correct_answer
        
        if question.question_type == QuestionType.MCQ:
            return str(user_answer).lower().strip() == correct.lower().strip()
        
        elif question.question_type == QuestionType.TRUE_FALSE:
            return str(user_answer).lower().strip() == correct.lower().strip()
        
        elif question.question_type == QuestionType.MULTI_SELECT:
            try:
                correct_set = set(json.loads(correct)) if isinstance(correct, str) else set(correct)
                user_set = set(user_answer) if isinstance(user_answer, list) else set(json.loads(user_answer))
                return correct_set == user_set
            except:
                return False
        
        elif question.question_type == QuestionType.SHORT_ANSWER:
            # Case-insensitive comparison, trimmed
            return str(user_answer).lower().strip() == correct.lower().strip()
        
        elif question.question_type == QuestionType.FILL_BLANK:
            return str(user_answer).lower().strip() == correct.lower().strip()
        
        elif question.question_type == QuestionType.MATCHING:
            try:
                correct_dict = json.loads(correct) if isinstance(correct, str) else correct
                user_dict = user_answer if isinstance(user_answer, dict) else json.loads(user_answer)
                return correct_dict == user_dict
            except:
                return False
        
        return False
    
    async def finish_attempt(
        self,
        attempt_id: int,
        user_id: int
    ) -> Optional[dict]:
        """Finish a quiz attempt and calculate final results"""
        attempt = await self.get_attempt(attempt_id, user_id)
        if not attempt or attempt.is_completed:
            return None
        
        quiz = await self.get_quiz(attempt.quiz_id, user_id, include_questions=True)
        if not quiz:
            return None
        
        # Mark as completed
        attempt.is_completed = True
        attempt.time_completed = datetime.utcnow()
        attempt.time_spent_seconds = int(
            (attempt.time_completed - attempt.time_started).total_seconds()
        )
        
        # Calculate score
        if attempt.points_possible > 0:
            attempt.score = (attempt.points_earned / attempt.points_possible) * 100
        else:
            attempt.score = 0
        
        # Analyze weak topics
        weak_topics = await self._analyze_weak_topics(attempt, quiz.questions)
        attempt.weak_topics = weak_topics
        
        # Update quiz stats
        quiz.times_taken += 1
        if quiz.average_score is None:
            quiz.average_score = attempt.score
        else:
            quiz.average_score = (
                (quiz.average_score * (quiz.times_taken - 1) + attempt.score) / quiz.times_taken
            )
        
        await self.db.flush()
        
        return await self._build_result_response(attempt, quiz)
    
    async def _analyze_weak_topics(
        self,
        attempt: QuizAttempt,
        questions: List[QuizQuestion]
    ) -> List[str]:
        """Analyze which topics the user struggled with"""
        topic_stats = {}
        
        # Build answer map
        answer_map = {a.question_id: a for a in attempt.answers}
        
        for question in questions:
            if not question.topic:
                continue
            
            if question.topic not in topic_stats:
                topic_stats[question.topic] = {"correct": 0, "total": 0}
            
            topic_stats[question.topic]["total"] += 1
            
            answer = answer_map.get(question.id)
            if answer and answer.is_correct:
                topic_stats[question.topic]["correct"] += 1
        
        # Find weak topics (< 70% accuracy)
        weak = []
        for topic, stats in topic_stats.items():
            if stats["total"] > 0:
                accuracy = stats["correct"] / stats["total"]
                if accuracy < 0.7:
                    weak.append(topic)
        
        return weak
    
    async def _build_result_response(
        self,
        attempt: QuizAttempt,
        quiz: Quiz
    ) -> dict:
        """Build detailed result response"""
        # Build answer map
        answer_map = {a.question_id: a for a in attempt.answers}
        
        # Analyze by difficulty, topic, type
        by_difficulty = {}
        by_topic = {}
        by_type = {}
        questions_detail = []
        
        for question in quiz.questions:
            answer = answer_map.get(question.id)
            is_correct = answer.is_correct if answer else False
            
            # By difficulty
            diff_key = str(question.difficulty)
            if diff_key not in by_difficulty:
                by_difficulty[diff_key] = {"correct": 0, "total": 0}
            by_difficulty[diff_key]["total"] += 1
            if is_correct:
                by_difficulty[diff_key]["correct"] += 1
            
            # By topic
            if question.topic:
                if question.topic not in by_topic:
                    by_topic[question.topic] = {"correct": 0, "total": 0}
                by_topic[question.topic]["total"] += 1
                if is_correct:
                    by_topic[question.topic]["correct"] += 1
            
            # By type
            type_key = question.question_type.value
            if type_key not in by_type:
                by_type[type_key] = {"correct": 0, "total": 0}
            by_type[type_key]["total"] += 1
            if is_correct:
                by_type[type_key]["correct"] += 1
            
            # Question detail
            questions_detail.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "user_answer": answer.user_answer if answer else None,
                "is_correct": is_correct,
                "points_earned": answer.points_earned if answer else 0,
                "points_possible": question.points,
                "explanation": question.explanation,
                "topic": question.topic
            })
        
        return {
            "attempt_id": attempt.id,
            "quiz_id": quiz.id,
            "quiz_name": quiz.name,
            "score": attempt.score,
            "points_earned": attempt.points_earned,
            "points_possible": attempt.points_possible,
            "correct_count": attempt.correct_count,
            "incorrect_count": attempt.incorrect_count,
            "time_spent_seconds": attempt.time_spent_seconds,
            "by_difficulty": by_difficulty,
            "by_topic": by_topic,
            "by_type": by_type,
            "weak_topics": attempt.weak_topics,
            "questions": questions_detail
        }
    
    async def get_user_attempts(
        self,
        user_id: int,
        quiz_id: Optional[int] = None,
        limit: int = 20
    ) -> List[QuizAttempt]:
        """Get quiz attempts for a user"""
        query = select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.is_completed == True
        )
        
        if quiz_id:
            query = query.where(QuizAttempt.quiz_id == quiz_id)
        
        query = query.order_by(QuizAttempt.time_completed.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
