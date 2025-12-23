"""
Celery Application Configuration
Background task queue for PDF processing and AI generation
"""

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    # Use mock for local development
    from app.celery_mock import Celery, celery_app as mock_celery_app
    CELERY_AVAILABLE = False

from app.config import settings


if CELERY_AVAILABLE:
    # Create real Celery app
    celery_app = Celery(
        "quizzr",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.tasks.document_tasks", "app.tasks.generation_tasks"]
    )
else:
    # Use mock Celery app for local development
    celery_app = mock_celery_app

# Celery configuration - only for real Celery
if CELERY_AVAILABLE:
    celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    
    # Rate limiting
    task_annotations={
        "app.tasks.generation_tasks.generate_deck_task": {
            "rate_limit": "10/m"  # 10 per minute
        },
        "app.tasks.generation_tasks.generate_quiz_task": {
            "rate_limit": "10/m"
        }
    },
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
        # Beat schedule for periodic tasks
        beat_schedule={
            "cleanup-old-jobs": {
                "task": "app.tasks.maintenance_tasks.cleanup_old_jobs",
                "schedule": 3600.0,  # Every hour
            },
            "update-study-streaks": {
                "task": "app.tasks.maintenance_tasks.update_study_streaks",
                "schedule": 86400.0,  # Daily
            }
        }
    )

    # Task routes
    celery_app.conf.task_routes = {
        "app.tasks.document_tasks.*": {"queue": "documents"},
        "app.tasks.generation_tasks.*": {"queue": "generation"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"}
    }

# Alias for imports
celery = celery_app
