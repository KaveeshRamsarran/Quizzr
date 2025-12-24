"""
Document Schemas
Request and response models for document-related endpoints
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    status: str
    job_id: int
    message: str


class DocumentPageResponse(BaseModel):
    """Schema for document page response"""
    id: int
    page_number: int
    text_content: Optional[str]
    text_length: int
    used_ocr: bool
    ocr_confidence: Optional[float]
    headings_on_page: Optional[List[str]]
    has_tables: bool
    has_images: bool
    
    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    """Schema for chunk response"""
    id: int
    chunk_index: int
    start_page: int
    end_page: int
    content: str
    content_length: int
    heading_context: Optional[str]
    parent_heading: Optional[str]
    key_terms: Optional[List[str]]
    content_type: str
    cards_generated: int
    questions_generated: int
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Schema for document response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str = "application/pdf"
    title: Optional[str]
    description: Optional[str]
    page_count: int
    style: str
    status: str
    processing_error: Optional[str]
    # Frontend compatibility
    error_message: Optional[str] = None
    ocr_used: bool
    ocr_pages: Optional[List[int]]
    headings: Optional[dict]
    table_of_contents: Optional[dict]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    
    # Related
    course_id: Optional[int]
    chunk_count: int = 0
    deck_count: int = 0
    quiz_count: int = 0
    
    @field_serializer("style")
    def serialize_style(self, value):
        if hasattr(value, "value"):
            return value.value
        return str(value) if value is not None else None

    @field_serializer("status")
    def serialize_status(self, value):
        """Map internal processing statuses to the simplified frontend statuses."""
        raw = value.value if hasattr(value, "value") else (str(value) if value is not None else "")
        raw = raw.lower()

        if raw in {"pending"}:
            return "pending"
        if raw in {"extracting", "chunking", "running", "processing"}:
            return "processing"
        if raw in {"completed", "processed"}:
            return "processed"
        if raw in {"failed", "error"}:
            return "error"

        return raw or "pending"

    @field_serializer("error_message")
    def serialize_error_message(self, value):
        # Prefer explicit value if set, else mirror processing_error
        if value is not None:
            return value
        # model may provide processing_error attribute
        return getattr(self, "processing_error", None)
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for document list response"""
    documents: List[DocumentResponse]
    total: int


class DocumentDetailResponse(DocumentResponse):
    """Schema for document detail with pages and chunks"""
    pages: List[DocumentPageResponse] = []
    chunks: List[ChunkResponse] = []


# Alias for compatibility
DocumentDetail = DocumentDetailResponse


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    course_id: Optional[int] = None
