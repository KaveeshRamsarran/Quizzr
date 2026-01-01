"""
Celery Application Configuration
Background task queue for PDF processing and AI generation
"""

from __future__ import annotations

from urllib.parse import urlparse

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    # Use mock for local development
    from app.celery_mock import Celery, celery_app as mock_celery_app
    CELERY_AVAILABLE = False

from app.config import settings


if CELERY_AVAILABLE:
    broker_url = (getattr(settings, "celery_broker_url", "") or "").strip() or settings.redis_url
    backend_url = (getattr(settings, "celery_result_backend", "") or "").strip() or settings.redis_url

    # Create real Celery app
    celery_app = Celery(
        "quizzr",
        broker=broker_url,
        backend=backend_url,
        include=["app.tasks.document_tasks", "app.tasks.generation_tasks"]
    )
else:
    # Use mock Celery app for local development
    celery_app = mock_celery_app

# Celery configuration - only for real Celery
if CELERY_AVAILABLE:
    # In local dev on Windows/macOS, users commonly don't have Redis/Celery running.
    # If the broker points at localhost, run tasks eagerly in-process so uploads and
    # generation still work.
    parsed = urlparse(str(celery_app.conf.broker_url or ""))
    broker_host = (parsed.hostname or "").lower()
    if settings.environment == "development" and broker_host in {"localhost", "127.0.0.1", "::1"}:
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

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
