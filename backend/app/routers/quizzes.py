"""
Quizzes Router
Handles quiz management and quiz attempts
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models.user import User
from app.models.quiz import Quiz, QuizQuestion, QuizAttempt
from app.models.course import Course
from app.schemas.quiz import (
    QuizCreate, QuizUpdate, QuizResponse, QuizDetail, QuizListResponse,
    QuizQuestionCreate, QuizQuestionUpdate, QuizQuestionResponse,
    QuizAttemptCreate, QuizAttemptResponse, QuizAttemptDetail,
    AnswerSubmission, AttemptResultResponse
)
from app.services.quiz import QuizService
from app.routers.dependencies import get_current_user

router = APIRouter(tags=["Quizzes"])


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_data: QuizCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new quiz
    """
    quiz_service = QuizService(session)
    
    # Verify course if provided
    if quiz_data.course_id:
        result = await session.execute(
            select(Course).where(
                Course.id == quiz_data.course_id,
                Course.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    quiz = await quiz_service.create_quiz(current_user.id, quiz_data)
    return QuizResponse.model_validate(quiz)


@router.get("", response_model=QuizListResponse)
@router.get("/", response_model=QuizListResponse)
async def list_quizzes(
    course_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List user's quizzes
    """
    query = select(Quiz).where(Quiz.user_id == current_user.id)
    
    if course_id:
        query = query.where(Quiz.course_id == course_id)
    
    if search:
        query = query.where(
            Quiz.name.ilike(f"%{search}%") |
            Quiz.description.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count(Quiz.id)).where(Quiz.user_id == current_user.id)
    if course_id:
        count_query = count_query.where(Quiz.course_id == course_id)
    
    total = (await session.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Quiz.updated_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    quizzes = result.scalars().all()
    
    return QuizListResponse(
        quizzes=[QuizResponse.model_validate(q) for q in quizzes],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{quiz_id}", response_model=QuizDetail)
async def get_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get quiz details including all questions
    """
    quiz_service = QuizService(session)
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id, include_questions=True)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return QuizDetail.model_validate(quiz)


@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: int,
    quiz_data: QuizUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update quiz metadata
    """
    quiz_service = QuizService(session)
    quiz = await quiz_service.update_quiz(quiz_id, current_user.id, quiz_data)
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return QuizResponse.model_validate(quiz)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a quiz and all its questions
    """
    quiz_service = QuizService(session)
    deleted = await quiz_service.delete_quiz(quiz_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )


# Question endpoints

@router.post("/{quiz_id}/questions", response_model=QuizQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    quiz_id: int,
    question_data: QuizQuestionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Add a question to a quiz
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Compatibility: older clients/tests send different option shapes and question_type values
    qtype = question_data.question_type
    if qtype == "multiple_choice":
        qtype = "mcq"

    options = question_data.options
    if options and isinstance(options, list) and options and isinstance(options[0], str):
        options = [{"id": str(i), "text": opt} for i, opt in enumerate(options)]

    question = await quiz_service.add_question(
        quiz_id=quiz_id,
        user_id=current_user.id,
        question_type=qtype,
        question_text=question_data.question_text,
        correct_answer=question_data.correct_answer,
        options=options,
        explanation=question_data.explanation,
        difficulty=question_data.difficulty,
        points=question_data.points,
        topic=question_data.topic,
        source_pages=question_data.source_pages,
        source_snippets=question_data.source_snippets,
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    return QuizQuestionResponse.model_validate(question)


@router.get("/{quiz_id}/questions", response_model=List[QuizQuestionResponse])
async def list_questions(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List all questions in a quiz
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    result = await session.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order)
    )
    questions = result.scalars().all()
    
    return [QuizQuestionResponse.model_validate(q) for q in questions]


@router.put("/{quiz_id}/questions/{question_id}", response_model=QuizQuestionResponse)
async def update_question(
    quiz_id: int,
    question_id: int,
    question_data: QuizQuestionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a question's content
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    question = await quiz_service.update_question(question_id, question_data)
    if not question or question.quiz_id != quiz_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    return QuizQuestionResponse.model_validate(question)


@router.delete("/{quiz_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    quiz_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a question from a quiz
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    deleted = await quiz_service.delete_question(question_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )


# Attempt endpoints

@router.post("/{quiz_id}/start", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{quiz_id}/attempts", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED)
async def start_quiz_attempt(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Start a new quiz attempt
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    attempt = await quiz_service.start_attempt(quiz_id, current_user.id)
    return QuizAttemptResponse.model_validate(attempt)


@router.get("/{quiz_id}/attempts", response_model=List[QuizAttemptResponse])
async def list_attempts(
    quiz_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List user's attempts for a quiz
    """
    quiz_service = QuizService(session)
    
    quiz = await quiz_service.get_quiz(quiz_id, current_user.id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    result = await session.execute(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.time_started.desc())
        .limit(limit)
    )
    attempts = result.scalars().all()
    
    return [QuizAttemptResponse.model_validate(a) for a in attempts]


@router.get("/{quiz_id}/attempts/{attempt_id}", response_model=QuizAttemptDetail)
async def get_attempt(
    quiz_id: int,
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get attempt details including all answers
    """
    result = await session.execute(
        select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id
        )
    )
    attempt = result.scalar_one_or_none()
    
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found"
        )
    
    return QuizAttemptDetail.model_validate(attempt)


@router.post("/{quiz_id}/attempts/{attempt_id}/answer", response_model=dict)
@router.post("/{quiz_id}/attempts/{attempt_id}/answers", response_model=dict)
async def submit_answer(
    quiz_id: int,
    attempt_id: int,
    answer: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit an answer for a question
    """
    quiz_service = QuizService(session)
    
    # Verify attempt
    result = await session.execute(
        select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id
        )
    )
    attempt = result.scalar_one_or_none()
    
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found"
        )
    
    if attempt.time_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt already completed"
        )
    
    # Submit answer
    result = await quiz_service.submit_answer(
        attempt_id=attempt_id,
        user_id=current_user.id,
        question_id=answer.question_id,
        answer=answer.answer,
        time_spent_seconds=(int(answer.time_spent_ms / 1000) if answer.time_spent_ms is not None else None),
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to submit answer",
        )

    return {
        "is_correct": result.get("is_correct", False),
        "feedback": result.get("explanation") or result.get("correct_answer"),
    }


@router.post("/{quiz_id}/attempts/{attempt_id}/finish", response_model=AttemptResultResponse)
async def finish_attempt(
    quiz_id: int,
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Finish a quiz attempt and get results
    """
    quiz_service = QuizService(session)

    # Load quiz for pass threshold
    quiz_result = await session.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == current_user.id)
    )
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )
    
    # Verify attempt
    result = await session.execute(
        select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id
        )
    )
    attempt = result.scalar_one_or_none()
    
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempt not found"
        )
    
    if attempt.time_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt already completed"
        )
    
    # Complete attempt
    results = await quiz_service.finish_attempt(attempt_id, current_user.id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to finish attempt",
        )
    
    await session.commit()
    
    # Ensure legacy fields expected by tests exist
    raw_score = float(results.get("score", 0) or 0) if isinstance(results, dict) else 0.0
    percentage = int(round(raw_score * 100)) if raw_score <= 1 else int(round(raw_score))
    passed = bool(percentage >= getattr(quiz, "pass_percentage", 70))
    if isinstance(results, dict):
        results.setdefault("completed", True)
        results.setdefault("percentage", percentage)
        results.setdefault("passed", passed)
    return AttemptResultResponse(**results)
