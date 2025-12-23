"""
API Routers Package
"""

from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.generation import router as generation_router
from app.routers.decks import router as decks_router
from app.routers.quizzes import router as quizzes_router
from app.routers.analytics import router as analytics_router
from app.routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "documents_router", 
    "generation_router",
    "decks_router",
    "quizzes_router",
    "analytics_router",
    "admin_router"
]
