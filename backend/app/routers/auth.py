"""
Authentication Router
Handles user registration, login, token management
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    TokenResponse, TokenRefresh, PasswordChange
)
from app.services.auth import AuthService
from app.routers.dependencies import get_current_user, security

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new user account
    Returns access and refresh tokens on successful registration
    """
    auth_service = AuthService(session)
    
    # Check if email already exists
    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await auth_service.create_user(user_data)
    
    # Generate tokens
    tokens = auth_service.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,  # 30 minutes
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Login with email and password
    Returns access and refresh tokens
    """
    auth_service = AuthService(session)
    
    result = await auth_service.login(
        email=credentials.email,
        password=credentials.password,
        ip_address=request.client.host if request.client else None
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user, tokens = result
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    session: AsyncSession = Depends(get_session)
):
    """
    Refresh access token using refresh token
    """
    auth_service = AuthService(session)
    
    result = await auth_service.refresh_tokens(token_data.refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user, tokens = result
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,
        user=UserResponse.model_validate(user)
    )


@router.post("/guest", response_model=TokenResponse)
async def create_guest(
    session: AsyncSession = Depends(get_session)
):
    """
    Create a guest account for trying the app without registration
    Guest accounts have limited features and expire after 30 days
    """
    auth_service = AuthService(session)
    
    user, tokens = await auth_service.create_guest_user()
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Logout the current user
    Invalidates the current refresh token
    """
    # In a production app, we would store the token in a blacklist
    # For now, we just return success
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update current user's profile
    """
    if user_data.name is not None:
        current_user.name = user_data.name

    if user_data.email is not None and user_data.email != current_user.email:
        auth_service = AuthService(session)
        existing = await auth_service.get_user_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = user_data.email
        current_user.is_verified = False

    if user_data.school is not None:
        current_user.school = user_data.school

    if user_data.timezone is not None:
        current_user.timezone = user_data.timezone

    if user_data.preferred_difficulty is not None:
        current_user.preferred_difficulty = user_data.preferred_difficulty

    if user_data.study_goal_days is not None:
        current_user.study_goal_days = user_data.study_goal_days

    if user_data.simple_mode is not None:
        current_user.simple_mode = user_data.simple_mode

    current_user.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Change the current user's password
    """
    auth_service = AuthService(session)
    
    # Verify current password
    if not auth_service.verify_password(
        password_data.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = auth_service.hash_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/convert-guest", response_model=TokenResponse)
async def convert_guest_to_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Convert a guest account to a full user account
    """
    if not current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not a guest account"
        )
    
    auth_service = AuthService(session)
    
    # Check if email is available
    existing = await auth_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Update guest account
    current_user.email = user_data.email.lower()
    current_user.hashed_password = auth_service.hash_password(user_data.password)
    current_user.name = user_data.name
    current_user.role = UserRole.STANDARD
    current_user.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(current_user)
    
    # Generate new tokens
    tokens = auth_service.create_tokens(current_user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=1800,
        user=UserResponse.model_validate(current_user)
    )
