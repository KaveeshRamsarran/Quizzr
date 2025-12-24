"""
Application Configuration
Loads settings from environment variables with validation
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Quizzr"
    environment: str = "development"
    debug: bool = True
    
    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./quizzr.db"
    
    # Redis (optional for local dev)
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-super-secret-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    # Optional: use an OpenAI-compatible local server by setting a base URL.
    # Example: http://localhost:8321/v1 (if your local server exposes /v1)
    openai_base_url: str = ""

    # Local/Pluggable LLM (recommended: Ollama)
    # llm_provider: 'ollama' (default) or 'openai' (OpenAI or OpenAI-compatible)
    llm_provider: str = "ollama"
    # Example Ollama models: 'llama3.1', 'llama3.1:8b', custom model name, etc.
    llm_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434"
    
    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "./uploads"
    allowed_extensions: str = "pdf"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Generation Limits
    max_cards_per_document: int = 500
    max_quiz_questions: int = 50
    max_chunks_per_generation: int = 20
    
    # Frontend URL (CORS)
    frontend_url: str = "http://localhost:5173"
    
    # OCR Settings
    ocr_enabled: bool = True
    ocr_text_threshold: int = 50
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    @property
    def cors_origins(self) -> List[str]:
        origins = [self.frontend_url]
        if self.environment == "development":
            origins.extend([
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
            ])
        return origins
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
