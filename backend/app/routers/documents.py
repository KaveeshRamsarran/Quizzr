"""
Documents Router
Handles PDF upload and document management
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.config import settings
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentPage, Chunk
from app.models.course import Course
from app.models.job import ProcessingJob, JobStatus, JobType
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentDetail,
    DocumentUpdate, DocumentPageResponse, ChunkResponse
)
from app.services.document import DocumentService
from app.routers.dependencies import get_current_user
from app.tasks import process_document_task

router = APIRouter(tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload a PDF document for processing
    The document will be queued for text extraction and can then be used for generation
    """
    doc_service = DocumentService(session)
    
    # Get file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    # Validate file
    is_valid, error = doc_service.validate_file(file.filename, file_size)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Check user's storage quota
    total_size = await session.execute(
        select(func.sum(Document.file_size)).where(Document.user_id == current_user.id)
    )
    current_usage = total_size.scalar() or 0
    
    max_storage = 500 * 1024 * 1024  # 500MB for free users
    if current_user.role == "premium":
        max_storage = 5 * 1024 * 1024 * 1024  # 5GB for premium
    
    if current_usage + file_size > max_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage quota exceeded"
        )
    
    # Verify course belongs to user if provided
    if course_id:
        result = await session.execute(
            select(Course).where(
                Course.id == course_id,
                Course.user_id == current_user.id
            )
        )
        course = result.scalar_one_or_none()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    # Read file content
    content = await file.read()
    file.file.seek(0)
    
    # Generate filename and compute hash
    filename = doc_service.generate_filename(file.filename, current_user.id)
    file_hash = doc_service.compute_file_hash(content)
    file_path = await doc_service.save_file(content, filename)
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        course_id=course_id,
        filename=filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
        status=DocumentStatus.PENDING
    )
    
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    # Create processing job
    job = ProcessingJob(
        user_id=current_user.id,
        job_type=JobType.PDF_EXTRACTION,
        document_id=document.id,
        status=JobStatus.PENDING,
        parameters={
            "ocr_enabled": settings.ocr_enabled,
            "ocr_threshold": settings.ocr_text_threshold,
        },
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    # Run processing (local dev uses celery_mock which executes synchronously)
    try:
        result = process_document_task.delay(job.id)
        if getattr(result, "state", "SUCCESS") == "FAILURE":
            job.status = JobStatus.FAILED
            job.error_message = str(getattr(result, "result", "Task failed"))
            document.status = DocumentStatus.FAILED
            document.processing_error = job.error_message
            await session.commit()
        else:
            # Processing writes via a separate sync session; reload document to reflect results
            await session.refresh(document)
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = f"Failed to run task: {str(e)}"
        document.status = DocumentStatus.FAILED
        document.processing_error = job.error_message
        await session.commit()
    
    return DocumentResponse.model_validate(document)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    course_id: Optional[int] = None,
    status: Optional[DocumentStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List user's documents with optional filtering
    """
    query = select(Document).where(Document.user_id == current_user.id)
    
    if course_id:
        query = query.where(Document.course_id == course_id)
    
    if status:
        query = query.where(Document.status == status)
    
    if search:
        query = query.where(
            Document.filename.ilike(f"%{search}%") |
            Document.title.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count(Document.id)).where(Document.user_id == current_user.id)
    if course_id:
        count_query = count_query.where(Document.course_id == course_id)
    if status:
        count_query = count_query.where(Document.status == status)
    
    total = (await session.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get document details including processing status and extracted content
    """
    # Load the base document
    doc_result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Load related content explicitly (avoid lazy-load / MissingGreenlet)
    pages_result = await session.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == document.id)
        .order_by(DocumentPage.page_number)
    )
    chunks_result = await session.execute(
        select(Chunk)
        .where(Chunk.document_id == document.id)
        .order_by(Chunk.chunk_index)
    )

    base = DocumentResponse.model_validate(document).model_dump()
    base["pages"] = [DocumentPageResponse.model_validate(p).model_dump() for p in pages_result.scalars().all()]
    base["chunks"] = [ChunkResponse.model_validate(c).model_dump() for c in chunks_result.scalars().all()]

    return DocumentDetail(**base)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update document metadata
    """
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if update_data.title is not None:
        document.title = update_data.title
    
    if update_data.description is not None:
        document.description = update_data.description
    
    if update_data.course_id is not None:
        # Verify course belongs to user
        if update_data.course_id:
            course_result = await session.execute(
                select(Course).where(
                    Course.id == update_data.course_id,
                    Course.user_id == current_user.id
                )
            )
            if not course_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Course not found"
                )
        document.course_id = update_data.course_id
    
    document.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(document)
    
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a document and its associated file
    """
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from storage
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError:
            pass  # File may already be deleted
    
    # Delete document record (cascades to pages and chunks)
    await session.delete(document)
    await session.commit()


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Reprocess a document that failed processing
    """
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status not in [DocumentStatus.ERROR, DocumentStatus.FAILED, DocumentStatus.PROCESSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document cannot be reprocessed in current state"
        )
    
    # Reset document status
    document.status = DocumentStatus.PENDING
    document.processing_error = None
    document.updated_at = datetime.utcnow()
    
    # Create new processing job
    job = ProcessingJob(
        user_id=current_user.id,
        job_type=JobType.PDF_EXTRACTION,
        document_id=document.id,
        status=JobStatus.PENDING,
        parameters={
            "reprocess": True,
            "ocr_enabled": settings.ocr_enabled,
            "ocr_threshold": settings.ocr_text_threshold,
        },
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await session.refresh(document)
    
    # Queue processing
    process_document_task.delay(job.id)
    
    return DocumentResponse.model_validate(document)
