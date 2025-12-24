"""
Admin Router
Handles administrative functions (admin users only)
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.deck import Deck
from app.models.quiz import Quiz, QuizAttempt
from app.models.job import ProcessingJob, JobStatus
from app.schemas.user import UserResponse
from app.routers.dependencies import get_admin_user

router = APIRouter(tags=["Admin"])


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get system-wide statistics
    """
    # User stats
    total_users = (await session.execute(select(func.count(User.id)))).scalar()
    active_users = (await session.execute(
        select(func.count(User.id)).where(
            User.last_active_at >= datetime.utcnow() - timedelta(days=7)
        )
    )).scalar()
    
    premium_users = (await session.execute(
        select(func.count(User.id)).where(User.role == UserRole.PREMIUM)
    )).scalar()
    
    guest_users = (await session.execute(
        select(func.count(User.id)).where(User.is_guest == True)
    )).scalar()
    
    # Content stats
    total_documents = (await session.execute(select(func.count(Document.id)))).scalar()
    total_decks = (await session.execute(select(func.count(Deck.id)))).scalar()
    total_quizzes = (await session.execute(select(func.count(Quiz.id)))).scalar()
    
    # Storage stats
    total_storage = (await session.execute(
        select(func.sum(Document.file_size))
    )).scalar() or 0
    
    # Job stats
    pending_jobs = (await session.execute(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status == JobStatus.PENDING
        )
    )).scalar()
    
    failed_jobs = (await session.execute(
        select(func.count(ProcessingJob.id)).where(
            ProcessingJob.status == JobStatus.FAILED,
            ProcessingJob.created_at >= datetime.utcnow() - timedelta(days=1)
        )
    )).scalar()
    
    return {
        "users": {
            "total": total_users,
            "active_7d": active_users,
            "premium": premium_users,
            "guests": guest_users
        },
        "content": {
            "documents": total_documents,
            "decks": total_decks,
            "quizzes": total_quizzes
        },
        "storage": {
            "total_bytes": total_storage,
            "total_mb": round(total_storage / (1024 * 1024), 2)
        },
        "jobs": {
            "pending": pending_jobs,
            "failed_24h": failed_jobs
        }
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List all users with filtering
    """
    query = select(User)
    
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.display_name.ilike(f"%{search}%")
        )
    
    if role:
        query = query.where(User.role == role)
    
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: UserRole,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a user's role
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    user.role = role
    user.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": f"User role updated to {role.value}"}


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Enable or disable a user account
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )
    
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": f"User {'enabled' if is_active else 'disabled'}"}


@router.get("/jobs")
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List processing jobs
    """
    query = select(ProcessingJob)
    
    if status:
        query = query.where(ProcessingJob.status == status)
    
    query = query.order_by(ProcessingJob.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    return [
        {
            "id": job.id,
            "job_type": job.job_type.value,
            "status": job.status.value,
            "user_id": job.user_id,
            "progress": job.progress,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }
        for job in jobs
    ]


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: int,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Retry a failed job
    """
    result = await session.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried"
        )
    
    # Reset job status
    job.status = JobStatus.PENDING
    job.error_message = None
    job.retry_count += 1
    job.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Re-queue the task based on job type
    from app.tasks import process_document_task, generate_deck_task, generate_quiz_task
    from app.models.job import JobType
    
    if job.job_type == JobType.DOCUMENT_PROCESSING:
        document_id = job.metadata.get("document_id")
        if document_id:
            process_document_task.delay(job.id)
    elif job.job_type == JobType.DECK_GENERATION:
        generate_deck_task.delay(job.id, job.metadata)
    elif job.job_type == JobType.QUIZ_GENERATION:
        generate_quiz_task.delay(job.id, job.metadata)
    
    return {"message": "Job queued for retry"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a user and all their data
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    await session.delete(user)
    await session.commit()
    
    return {"message": "User deleted"}
