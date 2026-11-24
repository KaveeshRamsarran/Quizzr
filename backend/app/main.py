"""
FastAPI Main Application
Entry point for the Quizzr API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import os

from app.config import settings
from app.database import engine, Base, upgrade_schema
import app.models  # noqa: F401  (register every table before create_all)
from app.services import jobs, storage
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
        await conn.run_sync(upgrade_schema)

    logger.info(
        "Database tables created/verified",
        auth="supabase" if settings.supabase_enabled else "built-in",
        file_storage="supabase" if storage.uses_supabase() else "local",
    )

    await storage.ensure_bucket()
    await jobs.recover_interrupted_jobs()

    yield

    # Shutdown
    logger.info("Shutting down Quizzr API")
    await jobs.wait_for_all()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Quizzr API",
    description="AI-powered flashcard and quiz generation from PDF documents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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


# Include routers
API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(documents.router, prefix=f"{API_V1_PREFIX}/documents", tags=["Documents"])
app.include_router(generation.router, prefix=f"{API_V1_PREFIX}/generation", tags=["Generation"])
app.include_router(decks.router, prefix=f"{API_V1_PREFIX}/decks", tags=["Decks"])
app.include_router(quizzes.router, prefix=f"{API_V1_PREFIX}/quizzes", tags=["Quizzes"])
app.include_router(analytics.router, prefix=f"{API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix=f"{API_V1_PREFIX}/admin", tags=["Admin"])


# Serve the built frontend (frontend/dist) when it exists, so one process runs the whole app.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", tags=["Root"])
    async def root():
        """API info (the frontend is served by Vite in development)."""
        return {"app": "Quizzr API", "version": "1.0.0", "docs": "/docs"}
