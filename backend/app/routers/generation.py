"""
Generation Router
Handles AI-powered flashcard and quiz generation
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.job import ProcessingJob, JobStatus, JobType
from app.schemas.generation import (
    DeckGenerationRequest, QuizGenerationRequest,
    GenerationJobResponse, GenerationJobStatus
)
from app.schemas.deck import DeckResponse
from app.schemas.quiz import QuizResponse
from app.routers.dependencies import get_current_user
from app.tasks import generate_deck_task, generate_quiz_task

router = APIRouter(tags=["Generation"])


@router.post("/deck", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_deck(
    request: DeckGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate a flashcard deck from a document
    Returns a job ID that can be polled for status
    """
    # Verify document exists and is processed
    result = await session.execute(
        select(Document).where(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status not in {DocumentStatus.PROCESSED, DocumentStatus.COMPLETED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for generation. Status: {document.status.value}"
        )
    
    # Create processing job
    job = ProcessingJob(
        user_id=current_user.id,
        job_type=JobType.DECK_GENERATION,
        status=JobStatus.PENDING,
        parameters=request.model_dump()
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    # Queue generation task (executes synchronously in local dev with celery_mock)
    try:
        result = generate_deck_task.delay(job.id, request.model_dump())
        # In local dev, task executes immediately; check for errors
        if hasattr(result, 'state') and result.state == 'FAILURE':
            job.status = JobStatus.FAILED
            job.error_message = str(getattr(result, 'result', 'Task failed'))
            await session.commit()
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to start generation: {str(e)}"
        await session.commit()
    
    # Refresh to get updated status
    await session.refresh(job)
    
    return GenerationJobResponse(
        job_id=job.id,
        status=GenerationJobStatus(job.status.value),
        message="Deck generation started" if job.status == JobStatus.PENDING else f"Generation {job.status.value}",
        progress=job.progress,
        result_id=None,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post("/quiz", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_quiz(
    request: QuizGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate a quiz from a document
    Returns a job ID that can be polled for status
    """
    # Verify document exists and is processed
    result = await session.execute(
        select(Document).where(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status not in {DocumentStatus.PROCESSED, DocumentStatus.COMPLETED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for generation. Status: {document.status.value}"
        )
    
    # Create processing job
    job = ProcessingJob(
        user_id=current_user.id,
        job_type=JobType.QUIZ_GENERATION,
        status=JobStatus.PENDING,
        parameters=request.model_dump()
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    # Queue generation task (executes synchronously in local dev with celery_mock)
    try:
        result = generate_quiz_task.delay(job.id, request.model_dump())
        # In local dev, task executes immediately; check for errors
        if hasattr(result, 'state') and result.state == 'FAILURE':
            job.status = JobStatus.FAILED
            job.error_message = str(getattr(result, 'result', 'Task failed'))
            await session.commit()
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to start generation: {str(e)}"
        await session.commit()
    
    # Refresh to get updated status
    await session.refresh(job)
    
    return GenerationJobResponse(
        job_id=job.id,
        status=GenerationJobStatus(job.status.value),
        message="Quiz generation started" if job.status == JobStatus.PENDING else f"Generation {job.status.value}",
        progress=job.progress,
        result_id=None,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/job/{job_id}", response_model=GenerationJobResponse)
async def get_generation_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get the status of a generation job
    """
    result = await session.execute(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Map job status to generation status
    status_map = {
        JobStatus.PENDING: GenerationJobStatus.PENDING,
        JobStatus.RUNNING: GenerationJobStatus.PROCESSING,
        JobStatus.RETRYING: GenerationJobStatus.PROCESSING,
        JobStatus.COMPLETED: GenerationJobStatus.COMPLETED,
        JobStatus.FAILED: GenerationJobStatus.FAILED,
        JobStatus.CANCELLED: GenerationJobStatus.FAILED,
    }
    
    result_id = None
    if job.result:
        result_id = job.result.get("deck_id") or job.result.get("quiz_id")

    return GenerationJobResponse(
        job_id=job.id,
        status=status_map.get(job.status, GenerationJobStatus.PENDING),
        message=job.error_message if job.status in {JobStatus.FAILED, JobStatus.CANCELLED} else None,
        progress=job.progress,
        result_id=result_id,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs", response_model=list[GenerationJobResponse])
async def list_generation_jobs(
    job_type: Optional[JobType] = None,
    status: Optional[JobStatus] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List user's generation jobs
    """
    query = select(ProcessingJob).where(
        ProcessingJob.user_id == current_user.id,
        ProcessingJob.job_type.in_([JobType.DECK_GENERATION, JobType.QUIZ_GENERATION])
    )
    
    if job_type:
        query = query.where(ProcessingJob.job_type == job_type)
    
    if status:
        query = query.where(ProcessingJob.status == status)
    
    query = query.order_by(ProcessingJob.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    status_map = {
        JobStatus.PENDING: GenerationJobStatus.PENDING,
        JobStatus.RUNNING: GenerationJobStatus.PROCESSING,
        JobStatus.RETRYING: GenerationJobStatus.PROCESSING,
        JobStatus.COMPLETED: GenerationJobStatus.COMPLETED,
        JobStatus.FAILED: GenerationJobStatus.FAILED,
        JobStatus.CANCELLED: GenerationJobStatus.FAILED,
    }
    
    return [
        GenerationJobResponse(
            job_id=job.id,
            status=status_map.get(job.status, GenerationJobStatus.PENDING),
            message=job.error_message if job.status in {JobStatus.FAILED, JobStatus.CANCELLED} else None,
            progress=job.progress,
            result_id=(job.result.get("deck_id") or job.result.get("quiz_id")) if job.result else None,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]


@router.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_generation_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Cancel a pending or processing generation job
    """
    result = await session.execute(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or failed job"
        )
    
    # Mark job as cancelled
    job.status = JobStatus.CANCELLED
    job.error_message = "Cancelled by user"
    job.completed_at = datetime.utcnow()
    
    # Revoke Celery task if possible
    if job.celery_task_id:
        from app.celery_app import celery
        celery.control.revoke(job.celery_task_id, terminate=True)
    
    await session.commit()
