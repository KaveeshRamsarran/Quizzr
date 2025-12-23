"""
User Schemas
Request and response models for user-related endpoints
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    school: Optional[str] = Field(None, max_length=255)
    timezone: str = Field(default="UTC", max_length=50)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    school: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = Field(None, max_length=50)
    preferred_difficulty: Optional[int] = Field(None, ge=1, le=5)
    study_goal_days: Optional[int] = Field(None, ge=1, le=365)
    simple_mode: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: str
    name: str
    school: Optional[str]
    timezone: str
    preferred_difficulty: int
    study_goal_days: Optional[int]
    simple_mode: bool
    role: str
    is_verified: bool
    study_streak: int
    total_study_time_minutes: int
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str


# Alias for compatibility
TokenRefresh = RefreshTokenRequest


class PasswordChange(BaseModel):
    """Schema for password change request"""
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class GuestUserCreate(BaseModel):
    """Schema for guest user creation"""
    # No fields required - generates temporary user
    pass
