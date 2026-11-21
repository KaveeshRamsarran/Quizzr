"""
Background jobs, run inside the API process.

Uploads and generation return straight away with a job id; the work runs as an
asyncio task with its own database session and the client polls for progress.
No Redis, Celery or separate worker is needed.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Callable, Coroutine, Set

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.document import Chunk, Document, DocumentPage, ProcessingStatus
from app.models.job import JobLog, JobStatus, JobType, ProcessingJob
from app.schemas.generation import DeckGenerationRequest, QuizGenerationRequest
from app.services import pdf_processing

logger = structlog.get_logger()

# Tests replace this with a factory bound to their database.
session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal
# When True, schedule() awaits the job instead of running it in the background.
run_inline: bool = False

_tasks: Set[asyncio.Task] = set()
OCR_TEXT_THRESHOLD = 40


async def schedule(job_runner: Callable[[int], Coroutine], job_id: int) -> None:
    """Run a job in the background (or inline when run_inline is set)."""
    if run_inline:
        await job_runner(job_id)
        return
    task = asyncio.create_task(job_runner(job_id), name=f"{job_runner.__name__}:{job_id}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def wait_for_all() -> None:
    """Await every running job (used on shutdown and in tests)."""
    while _tasks:
        await asyncio.gather(*list(_tasks), return_exceptions=True)


def resolve_upload_path(stored_path: str) -> str:
    if os.path.isabs(stored_path):
        return stored_path
    base = os.path.abspath(settings.upload_dir)
    candidate = os.path.join(base, os.path.basename(stored_path))
    return candidate


# --------------------------------------------------------------------------- #
# Document processing
# --------------------------------------------------------------------------- #

def _process_pdf(file_path: str) -> dict:
    """CPU-bound part of processing; runs in a worker thread."""
    raw_pages = pdf_processing.extract_pdf_pages(file_path)
    if not raw_pages:
        raise ValueError("This PDF has no pages.")

    ocr_pages = []
    for page in raw_pages:
        if len(page["text"].strip()) < OCR_TEXT_THRESHOLD:
            text, confidence = pdf_processing.run_ocr_on_page(file_path, page["page_number"])
            if len(text) > len(page["text"]):
                page.update(text=text, used_ocr=True, ocr_confidence=confidence)
                ocr_pages.append(page["page_number"])

    pages = pdf_processing.clean_pages(raw_pages)
    if sum(len(p["text"]) for p in pages) < 80:
        raise ValueError(
            "No readable text was found in this PDF. It looks scanned or image-only; "
            "export it with selectable text and upload it again."
        )
    style, headings = pdf_processing.analyze_document_structure(pages)
    chunks = pdf_processing.create_chunks(pages, style)
    title = None
    first_headings = [h for p in pages[:2] for h in p.get("headings", [])]
    if first_headings:
        title = first_headings[0][:255]
    return {"pages": pages, "style": style, "headings": headings, "chunks": chunks, "ocr_pages": ocr_pages, "title": title}


async def run_document_job(job_id: int) -> None:
    async with session_factory() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job:
            return
        document = await session.get(Document, job.document_id) if job.document_id else None
        if not document:
            job.status = JobStatus.FAILED
            job.error_message = "Document not found"
            await session.commit()
            return

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.current_step = "Extracting text"
            job.progress = 10
            document.status = ProcessingStatus.EXTRACTING
            document.processing_error = None
            await session.commit()

            path = resolve_upload_path(document.file_path)
            if not os.path.exists(path):
                raise ValueError("The uploaded file is missing from storage. Upload it again.")

            data = await asyncio.to_thread(_process_pdf, path)

            job.current_step = "Saving pages"
            job.progress = 70
            document.status = ProcessingStatus.CHUNKING
            await session.commit()

            # Replace any earlier extraction (reprocessing).
            for model in (DocumentPage, Chunk):
                rows = (await session.execute(select(model).where(model.document_id == document.id))).scalars().all()
                for row in rows:
                    await session.delete(row)
            await session.flush()

            for page in data["pages"]:
                text = pdf_processing.display_text(page["text"])
                session.add(DocumentPage(
                    document_id=document.id,
                    page_number=page["page_number"],
                    text_content=text,
                    text_length=len(text),
                    used_ocr=page.get("used_ocr", False),
                    ocr_confidence=page.get("ocr_confidence"),
                    headings_on_page=page.get("headings") or None,
                    has_tables=False,
                    has_images=page.get("has_images", False),
                ))
            for index, chunk in enumerate(data["chunks"]):
                session.add(Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    start_page=chunk["start_page"],
                    end_page=chunk["end_page"],
                    content=chunk["content"],
                    content_length=len(chunk["content"]),
                    heading_context=(chunk.get("heading_context") or None) and chunk["heading_context"][:512],
                    parent_heading=(chunk.get("parent_heading") or None) and chunk["parent_heading"][:255],
                    key_terms=chunk.get("key_terms"),
                    content_type=chunk.get("content_type", "text"),
                ))

            document.page_count = len(data["pages"])
            document.style = data["style"]
            document.headings = data["headings"]
            document.ocr_used = bool(data["ocr_pages"])
            document.ocr_pages = data["ocr_pages"] or None
            if not document.title:
                document.title = data["title"] or document.original_filename.rsplit(".", 1)[0][:255]
            document.status = ProcessingStatus.PROCESSED
            document.processed_at = datetime.utcnow()

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.current_step = "Completed"
            job.progress = 100
            job.result = {"page_count": document.page_count, "chunk_count": len(data["chunks"]), "style": data["style"].value}
            session.add(JobLog(job_id=job.id, level="info",
                               message=f"Processed {document.page_count} pages into {len(data['chunks'])} chunks"))
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Document processing failed", job_id=job_id, error=str(exc))
            job = await session.get(ProcessingJob, job_id)
            document = await session.get(Document, job.document_id) if job else None
            message = str(exc) if isinstance(exc, ValueError) else f"Processing failed: {exc}"
            if job:
                job.status = JobStatus.FAILED
                job.error_message = message
                job.completed_at = datetime.utcnow()
                session.add(JobLog(job_id=job.id, level="error", message=message))
            if document:
                document.status = ProcessingStatus.FAILED
                document.processing_error = message
            await session.commit()


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

async def _run_generation(job_id: int, kind: str) -> None:
    from app.services.generation import GenerationService

    async with session_factory() as session:
        job = await session.get(ProcessingJob, job_id)
        if not job or job.status == JobStatus.CANCELLED:
            return

        async def progress(value: float, step: str) -> None:
            await session.refresh(job, attribute_names=["status"])
            if job.status == JobStatus.CANCELLED:
                raise asyncio.CancelledError("Cancelled by user")
            job.progress = round(min(99.0, value), 1)
            job.current_step = step
            await session.commit()

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            await session.commit()

            service = GenerationService(session)
            params = dict(job.parameters or {})
            if kind == "deck":
                await service.generate_deck(job.user_id, DeckGenerationRequest(**params), job, progress)
            else:
                await service.generate_quiz(job.user_id, QuizGenerationRequest(**params), job, progress)

            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.current_step = "Completed"
            job.completed_at = datetime.utcnow()
            await session.commit()
        except asyncio.CancelledError:
            await session.rollback()
        except Exception as exc:
            await session.rollback()
            logger.error("Generation failed", job_id=job_id, kind=kind, error=str(exc))
            job = await session.get(ProcessingJob, job_id)
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.FAILED
                job.error_message = str(exc) if isinstance(exc, ValueError) else f"Generation failed: {exc}"
                job.completed_at = datetime.utcnow()
                session.add(JobLog(job_id=job.id, level="error", message=job.error_message))
                await session.commit()


async def run_deck_job(job_id: int) -> None:
    await _run_generation(job_id, "deck")


async def run_quiz_job(job_id: int) -> None:
    await _run_generation(job_id, "quiz")


RUNNERS = {
    JobType.PDF_EXTRACTION: run_document_job,
    JobType.DECK_GENERATION: run_deck_job,
    JobType.QUIZ_GENERATION: run_quiz_job,
}


async def recover_interrupted_jobs() -> None:
    """On startup, restart document processing and fail generation jobs cut off by a restart."""
    async with session_factory() as session:
        jobs = (await session.execute(
            select(ProcessingJob).where(ProcessingJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]))
        )).scalars().all()
        restart = []
        for job in jobs:
            if job.job_type == JobType.PDF_EXTRACTION:
                job.status = JobStatus.PENDING
                restart.append(job.id)
            else:
                job.status = JobStatus.FAILED
                job.error_message = "Interrupted by a server restart. Start the generation again."
                job.completed_at = datetime.utcnow()
        await session.commit()
    for job_id in restart:
        await schedule(run_document_job, job_id)
