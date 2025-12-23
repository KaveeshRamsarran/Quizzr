"""
Tasks Package
Celery background tasks
"""

from app.tasks.document_tasks import process_document_task
from app.tasks.generation_tasks import (
    generate_deck_task,
    generate_quiz_task,
    verify_content_task
)
from app.tasks.maintenance_tasks import (
    update_user_streaks,
    cleanup_expired_jobs,
    cleanup_orphaned_files,
    cleanup_guest_accounts,
    recalculate_spaced_repetition,
    generate_daily_stats
)

__all__ = [
    "process_document_task",
    "generate_deck_task",
    "generate_quiz_task",
    "verify_content_task",
    "update_user_streaks",
    "cleanup_expired_jobs",
    "cleanup_orphaned_files",
    "cleanup_guest_accounts",
    "recalculate_spaced_repetition",
    "generate_daily_stats"
]