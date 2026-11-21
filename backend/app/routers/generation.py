"""
Generation Router
Starts flashcard and quiz generation jobs and reports their progress.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.document import Document, DocumentStatus
from app.models.job import JobStatus, JobType, ProcessingJob
from app.models.user import User
from app.routers.dependencies import get_current_user
from app.schemas.generation import (
    DeckGenerationRequest,
    GenerationJobResponse,
    GenerationJobStatus,
    QuizGenerationRequest,
)
from app.services import jobs

router = APIRouter(tags=["Generation"])

STATUS_MAP = {
    JobStatus.PENDING: GenerationJobStatus.PENDING,
    JobStatus.RUNNING: GenerationJobStatus.PROCESSING,
    JobStatus.RETRYING: GenerationJobStatus.PROCESSING,
    JobStatus.COMPLETED: GenerationJobStatus.COMPLETED,
    JobStatus.FAILED: GenerationJobStatus.FAILED,
    JobStatus.CANCELLED: GenerationJobStatus.FAILED,
}


def to_response(job: ProcessingJob) -> GenerationJobResponse:
    result = job.result or {}
    failed = job.status in {JobStatus.FAILED, JobStatus.CANCELLED}
    return GenerationJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=STATUS_MAP.get(job.status, GenerationJobStatus.PENDING),
        message=job.error_message if failed else job.current_step,
        step=job.current_step,
        progress=job.progress,
        result_id=result.get("deck_id") or result.get("quiz_id"),
        document_id=(job.parameters or {}).get("document_id") or job.document_id,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


async def _ready_document(session: AsyncSession, document_id: int, user: User) -> Document:
    document = (await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status not in {DocumentStatus.PROCESSED, DocumentStatus.COMPLETED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document is still being processed or failed to process.",
        )
    return document


async def _start(session: AsyncSession, user: User, job_type: JobType, request, runner) -> ProcessingJob:
    job = ProcessingJob(
        user_id=user.id,
        job_type=job_type,
        document_id=request.document_id,
        status=JobStatus.PENDING,
        current_step="Queued",
        parameters=request.model_dump(mode="json"),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await jobs.schedule(runner, job.id)
    if jobs.run_inline:
        await session.refresh(job)
    return job


@router.post("/deck", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_deck(
    request: DeckGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Start generating a flashcard deck from a processed document."""
    await _ready_document(session, request.document_id, current_user)
    job = await _start(session, current_user, JobType.DECK_GENERATION, request, jobs.run_deck_job)
    return to_response(job)


@router.post("/quiz", response_model=GenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_quiz(
    request: QuizGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Start generating a quiz from a processed document."""
    await _ready_document(session, request.document_id, current_user)
    job = await _start(session, current_user, JobType.QUIZ_GENERATION, request, jobs.run_quiz_job)
    return to_response(job)


@router.get("/job/{job_id}", response_model=GenerationJobResponse)
@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the status of a generation job."""
    if not job_id.isdigit():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job = (await session.execute(
        select(ProcessingJob).where(ProcessingJob.id == int(job_id), ProcessingJob.user_id == current_user.id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return to_response(job)


@router.get("/jobs", response_model=list[GenerationJobResponse])
async def list_generation_jobs(
    job_type: Optional[JobType] = None,
    job_status: Optional[JobStatus] = Query(None, alias="status"),
    document_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List the user's recent generation jobs."""
    query = select(ProcessingJob).where(
        ProcessingJob.user_id == current_user.id,
        ProcessingJob.job_type.in_([JobType.DECK_GENERATION, JobType.QUIZ_GENERATION]),
    )
    if job_type:
        query = query.where(ProcessingJob.job_type == job_type)
    if job_status:
        query = query.where(ProcessingJob.status == job_status)
    if document_id:
        query = query.where(ProcessingJob.document_id == document_id)
    result = await session.execute(query.order_by(ProcessingJob.created_at.desc()).limit(limit))
    return [to_response(job) for job in result.scalars().all()]


@router.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_generation_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel a pending or running generation job."""
    job = (await session.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.user_id == current_user.id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a running job can be cancelled")
    job.status = JobStatus.CANCELLED
    job.error_message = "Cancelled"
    job.completed_at = datetime.utcnow()
    await session.commit()
