"""
Course Schemas
Request and response models for course-related endpoints
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    """Schema for creating a course"""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="book", max_length=50)
    semester: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = Field(None, ge=2000, le=2100)


class CourseUpdate(BaseModel):
    """Schema for updating a course"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    semester: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = Field(None, ge=2000, le=2100)


class CourseResponse(BaseModel):
    """Schema for course response"""
    id: int
    name: str
    description: Optional[str]
    color: str
    icon: str
    semester: Optional[str]
    year: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    # Counts
    document_count: int = 0
    deck_count: int = 0
    quiz_count: int = 0
    
    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    """Schema for course list response"""
    courses: list[CourseResponse]
    total: int
