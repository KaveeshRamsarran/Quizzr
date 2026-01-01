"""
Maintenance Tasks
Celery periodic tasks for system maintenance and data cleanup
"""

from datetime import datetime, timedelta
import structlog

try:
    from celery import shared_task
except ImportError:
    from app.celery_mock import shared_task

from sqlalchemy import create_engine, select, func, and_
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.job import ProcessingJob, JobStatus
from app.models.spaced_repetition import SpacedRepetitionSchedule

logger = structlog.get_logger()


def get_sync_session() -> Session:
    """Get a synchronous database session for Celery tasks"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@shared_task
def update_user_streaks() -> dict:
    """
    Update user study streaks daily
    Checks if users studied yesterday and updates streak accordingly
    """
    session = get_sync_session()
    
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        users_updated = 0
        streaks_reset = 0
        
        # Get all active users
        users = session.execute(select(User).where(User.is_active == True)).scalars().all()
        
        for user in users:
            last_study = user.last_study_at.date() if user.last_study_at else None
            
            if last_study == yesterday:
                # User studied yesterday, streak continues
                pass
            elif last_study == today:
                # User studied today, streak is already updated
                pass
            else:
                # User missed a day, reset streak
                if user.current_streak > 0:
                    user.current_streak = 0
                    streaks_reset += 1
            
            users_updated += 1
        
        session.commit()
        
        logger.info(
            "user_streaks_updated",
            users_updated=users_updated,
            streaks_reset=streaks_reset
        )
        
        return {
            "users_updated": users_updated,
            "streaks_reset": streaks_reset
        }
        
    except Exception as e:
        session.rollback()
        logger.error("streak_update_failed", error=str(e))
        raise
    finally:
        session.close()


@shared_task
def cleanup_expired_jobs() -> dict:
    """
    Clean up old completed/failed jobs and their logs
    Keeps jobs for 7 days after completion
    """
    session = get_sync_session()
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Find old completed/failed jobs
        old_jobs = session.execute(
            select(ProcessingJob).where(
                and_(
                    ProcessingJob.completed_at < cutoff,
                    ProcessingJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
                )
            )
        ).scalars().all()
        
        deleted_count = len(old_jobs)
        
        for job in old_jobs:
            session.delete(job)
        
        session.commit()
        
        logger.info(
            "expired_jobs_cleaned",
            deleted_count=deleted_count
        )
        
        return {"deleted_jobs": deleted_count}
        
    except Exception as e:
        session.rollback()
        logger.error("job_cleanup_failed", error=str(e))
        raise
    finally:
        session.close()


@shared_task
def cleanup_orphaned_files() -> dict:
    """
    Clean up uploaded files that are no longer referenced by documents
    """
    import os
    import shutil
    
    session = get_sync_session()
    
    try:
        upload_dir = settings.upload_dir
        files_deleted = 0
        bytes_freed = 0
        
        if not os.path.exists(upload_dir):
            return {"files_deleted": 0, "bytes_freed": 0}
        
        # Get all document file paths from database
        documents = session.execute(select(Document.file_path)).scalars().all()
        referenced_paths = set(documents)
        
        # Walk through upload directory
        for root, dirs, files in os.walk(upload_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                if file_path not in referenced_paths:
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_deleted += 1
                        bytes_freed += file_size
                    except OSError as e:
                        logger.warning("file_delete_failed", path=file_path, error=str(e))
        
        logger.info(
            "orphaned_files_cleaned",
            files_deleted=files_deleted,
            bytes_freed=bytes_freed
        )
        
        return {
            "files_deleted": files_deleted,
            "bytes_freed": bytes_freed
        }
        
    except Exception as e:
        session.rollback()
        logger.error("file_cleanup_failed", error=str(e))
        raise
    finally:
        session.close()


@shared_task
def cleanup_guest_accounts() -> dict:
    """
    Clean up old guest accounts and their data
    Guest accounts are deleted after 30 days of inactivity
    """
    session = get_sync_session()
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        # Find old guest accounts
        old_guests = session.execute(
            select(User).where(
                and_(
                    User.is_guest == True,
                    User.last_active_at < cutoff
                )
            )
        ).scalars().all()
        
        deleted_count = len(old_guests)
        
        for guest in old_guests:
            # Delete all user data (cascades will handle related records)
            session.delete(guest)
        
        session.commit()
        
        logger.info(
            "guest_accounts_cleaned",
            deleted_count=deleted_count
        )
        
        return {"deleted_guests": deleted_count}
        
    except Exception as e:
        session.rollback()
        logger.error("guest_cleanup_failed", error=str(e))
        raise
    finally:
        session.close()


@shared_task
def recalculate_spaced_repetition() -> dict:
    """
    Recalculate overdue spaced repetition schedules
    Updates priority for cards that are past their due date
    """
    session = get_sync_session()
    
    try:
        now = datetime.utcnow()
        
        # Find overdue schedules
        overdue = session.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.next_review < now
            )
        ).scalars().all()
        
        updated = 0
        for schedule in overdue:
            # Calculate days overdue
            days_overdue = (now - schedule.next_review).days
            
            # Increase priority based on how overdue
            if days_overdue > 7:
                schedule.easiness = max(1.3, schedule.easiness - 0.1)
            
            updated += 1
        
        session.commit()
        
        logger.info(
            "spaced_repetition_recalculated",
            updated=updated
        )
        
        return {"schedules_updated": updated}
        
    except Exception as e:
        session.rollback()
        logger.error("sr_recalculation_failed", error=str(e))
        raise
    finally:
        session.close()


@shared_task
def generate_daily_stats() -> dict:
    """
    Generate daily statistics for analytics
    Aggregates user activity for the previous day
    """
    session = get_sync_session()
    
    try:
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = datetime.combine(yesterday, datetime.max.time())
        
        # Count active users
        active_users = session.execute(
            select(func.count(User.id)).where(
                and_(
                    User.last_active_at >= yesterday_start,
                    User.last_active_at <= yesterday_end
                )
            )
        ).scalar()
        
        # Count new users
        new_users = session.execute(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= yesterday_start,
                    User.created_at <= yesterday_end
                )
            )
        ).scalar()
        
        # Count documents uploaded
        from app.models.document import Document
        documents_uploaded = session.execute(
            select(func.count(Document.id)).where(
                and_(
                    Document.created_at >= yesterday_start,
                    Document.created_at <= yesterday_end
                )
            )
        ).scalar()
        
        stats = {
            "date": yesterday.isoformat(),
            "active_users": active_users or 0,
            "new_users": new_users or 0,
            "documents_uploaded": documents_uploaded or 0
        }
        
        logger.info("daily_stats_generated", **stats)
        
        return stats
        
    except Exception as e:
        session.rollback()
        logger.error("stats_generation_failed", error=str(e))
        raise
    finally:
        session.close()
