"""
FastAPI Main Application
Entry point for the Quizzr API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import os

from app.config import settings
from app.database import engine, Base
from app.routers import auth, documents, generation, decks, quizzes, analytics, admin


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Quizzr API", environment=settings.environment)
    
    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Quizzr API")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Quizzr API",
    description="AI-powered flashcard and quiz generation from PDF documents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    from datetime import datetime
    error_trace = traceback.format_exc()
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=error_trace,
        path=request.url.path,
        method=request.method,
    )
    print(f"ERROR: {type(exc).__name__}: {str(exc)}")
    print(f"TRACEBACK:\n{error_trace}")

    # Also write to a local log file to make debugging easier in dev
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "errors.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"[{datetime.utcnow().isoformat()}Z] {request.method} {request.url.path}\n")
            f.write(f"{type(exc).__name__}: {str(exc)}\n")
            f.write(error_trace)
    except Exception:
        # Never fail the request due to logging issues
        pass

    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info"""
    return {
        "app": "Quizzr API",
        "version": "1.0.0",
        "description": "AI-powered flashcard and quiz generation",
        "docs": "/docs" if settings.debug else "Disabled in production",
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(generation.router, prefix="/generate", tags=["Generation"])
app.include_router(decks.router, prefix="/decks", tags=["Decks"])
app.include_router(quizzes.router, prefix="/quizzes", tags=["Quizzes"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
