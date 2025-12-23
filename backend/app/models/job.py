"""
Processing Job Models
Background job tracking for PDF processing and generation
"""

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Enum, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(str, enum.Enum):
    """Job type enumeration"""
    PDF_EXTRACTION = "pdf_extraction"
    OCR_PROCESSING = "ocr_processing"
    CHUNKING = "chunking"
    DECK_GENERATION = "deck_generation"
    QUIZ_GENERATION = "quiz_generation"
    VERIFICATION = "verification"


class ProcessingJob(Base):
    """Background processing job model"""
    __tablename__ = "processing_jobs"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Job info
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType),
        nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        index=True
    )
    
    # Celery task info
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Related entities
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    deck_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quiz_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Job parameters
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=1)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    
    # Results
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Retry info
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    logs: Mapped[list["JobLog"]] = relationship(
        "JobLog",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobLog.created_at"
    )
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None
    
    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.status})>"


class JobLog(Base):
    """Log entry for a processing job"""
    __tablename__ = "job_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Log info
    level: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    job: Mapped["ProcessingJob"] = relationship("ProcessingJob", back_populates="logs")
    
    def __repr__(self) -> str:
        return f"<JobLog(job_id={self.job_id}, level={self.level})>"
