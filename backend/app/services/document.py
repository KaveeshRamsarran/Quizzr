"""
Document Service
Handles PDF upload, storage, and management
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import aiofiles

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.document import Document, DocumentPage, Chunk, ProcessingStatus
from app.models.job import ProcessingJob, JobType, JobStatus
from app.schemas.document import DocumentResponse, DocumentDetailResponse


class DocumentService:
    """Service for document management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
        """Validate uploaded file"""
        # Check extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.allowed_extensions_list:
            return False, f"File type '.{ext}' not allowed. Allowed: {settings.allowed_extensions}"
        
        # Check size
        if file_size > settings.max_upload_size_bytes:
            return False, f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
        
        return True, ""
    
    @staticmethod
    def generate_filename(original_filename: str, user_id: int) -> str:
        """Generate a unique filename for storage"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "pdf"
        safe_name = "".join(c for c in original_filename.rsplit(".", 1)[0] if c.isalnum() or c in "._- ")[:50]
        return f"{user_id}_{timestamp}_{safe_name}.{ext}"
    
    @staticmethod
    def compute_file_hash(content: bytes) -> str:
        """Compute SHA256 hash of file content"""
        return hashlib.sha256(content).hexdigest()
    
    async def save_file(self, content: bytes, filename: str) -> str:
        """Save file to upload directory"""
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        return str(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False
    
    async def create_document(
        self,
        user_id: int,
        original_filename: str,
        content: bytes,
        course_id: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> tuple[Document, ProcessingJob]:
        """Create a new document and start processing job"""
        # Generate storage filename
        filename = self.generate_filename(original_filename, user_id)
        file_hash = self.compute_file_hash(content)
        
        # Check for duplicate
        existing = await self.db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.file_hash == file_hash
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("This file has already been uploaded")
        
        # Save file
        file_path = await self.save_file(content, filename)
        
        # Create document record
        document = Document(
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=len(content),
            file_hash=file_hash,
            title=title or original_filename.rsplit(".", 1)[0],
            description=description,
            status=ProcessingStatus.PENDING
        )
        
        self.db.add(document)
        await self.db.flush()
        
        # Create processing job
        job = ProcessingJob(
            user_id=user_id,
            job_type=JobType.PDF_EXTRACTION,
            status=JobStatus.PENDING,
            document_id=document.id,
            parameters={
                "ocr_enabled": settings.ocr_enabled,
                "ocr_threshold": settings.ocr_text_threshold
            }
        )
        
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(document)
        await self.db.refresh(job)
        
        return document, job
    
    async def get_document(self, document_id: int, user_id: int) -> Optional[Document]:
        """Get a document by ID"""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
            .options(
                selectinload(Document.pages),
                selectinload(Document.chunks)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_documents(
        self,
        user_id: int,
        course_id: Optional[int] = None,
        status: Optional[ProcessingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Document], int]:
        """Get documents for a user with filtering"""
        query = select(Document).where(Document.user_id == user_id)
        count_query = select(func.count(Document.id)).where(Document.user_id == user_id)
        
        if course_id is not None:
            query = query.where(Document.course_id == course_id)
            count_query = count_query.where(Document.course_id == course_id)
        
        if status is not None:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        
        # Get total count
        total = await self.db.execute(count_query)
        total_count = total.scalar()
        
        # Get documents
        query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        documents = list(result.scalars().all())
        
        return documents, total_count
    
    async def update_document(
        self,
        document_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        course_id: Optional[int] = None
    ) -> Optional[Document]:
        """Update document metadata"""
        document = await self.get_document(document_id, user_id)
        if not document:
            return None
        
        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        if course_id is not None:
            document.course_id = course_id
        
        document.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(document)
        return document
    
    async def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document and its file"""
        document = await self.get_document(document_id, user_id)
        if not document:
            return False
        
        # Delete file
        await self.delete_file(document.file_path)
        
        # Delete record (cascades to pages, chunks)
        await self.db.delete(document)
        await self.db.flush()
        return True
    
    async def get_document_pages(
        self,
        document_id: int,
        user_id: int
    ) -> List[DocumentPage]:
        """Get all pages for a document"""
        document = await self.get_document(document_id, user_id)
        if not document:
            return []
        
        result = await self.db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
        return list(result.scalars().all())
    
    async def get_document_chunks(
        self,
        document_id: int,
        user_id: int
    ) -> List[Chunk]:
        """Get all chunks for a document"""
        document = await self.get_document(document_id, user_id)
        if not document:
            return []
        
        result = await self.db.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return list(result.scalars().all())
    
    async def search_documents(
        self,
        user_id: int,
        query: str,
        limit: int = 20
    ) -> List[Document]:
        """Search documents by title and content"""
        # Simple search by title (full-text search would be better)
        result = await self.db.execute(
            select(Document)
            .where(
                Document.user_id == user_id,
                Document.title.ilike(f"%{query}%")
            )
            .limit(limit)
        )
        return list(result.scalars().all())
