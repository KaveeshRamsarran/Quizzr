"""
Authentication Service
Handles user registration, login, JWT tokens
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserUpdate, TokenResponse, UserResponse


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for user management and JWT handling"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        
        expire = datetime.utcnow() + expires_delta
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def create_refresh_token() -> tuple[str, datetime]:
        """Create a refresh token and its expiration"""
        token = secrets.token_urlsafe(64)
        expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        return token, expires
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[int]:
        """Decode and validate an access token, return user_id if valid"""
        try:
            payload = jwt.decode(
                token, 
                settings.secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            if payload.get("type") != "access":
                return None
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
        except JWTError:
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if email already exists
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            email=user_data.email.lower(),
            hashed_password=self.hash_password(user_data.password),
            name=user_data.name,
            school=user_data.school,
            timezone=user_data.timezone,
            role=UserRole.STANDARD,
            is_active=True,
            is_verified=False,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def create_guest_user(self) -> User:
        """Create a temporary guest user"""
        # Generate unique guest email
        guest_id = secrets.token_hex(8)
        guest_email = f"guest_{guest_id}@quizzr.temp"
        
        user = User(
            email=guest_email,
            hashed_password=self.hash_password(secrets.token_urlsafe(32)),
            name=f"Guest {guest_id[:6]}",
            role=UserRole.GUEST,
            is_active=True,
            is_verified=False,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = await self.get_user_by_email(login_data.email)
        if not user:
            return None
        if not self.verify_password(login_data.password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    async def login(self, login_data: UserLogin) -> Optional[TokenResponse]:
        """Login user and return tokens"""
        user = await self.authenticate_user(login_data)
        if not user:
            return None
        
        # Create tokens
        access_token = self.create_access_token(user.id)
        refresh_token, refresh_expires = self.create_refresh_token()
        
        # Store refresh token
        user.refresh_token = refresh_token
        user.refresh_token_expires = refresh_expires
        user.last_login = datetime.utcnow()
        await self.db.flush()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user)
        )
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh access token using refresh token"""
        # Find user with this refresh token
        result = await self.db.execute(
            select(User).where(
                User.refresh_token == refresh_token,
                User.refresh_token_expires > datetime.utcnow()
            )
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        # Create new tokens
        access_token = self.create_access_token(user.id)
        new_refresh_token, refresh_expires = self.create_refresh_token()
        
        # Update refresh token
        user.refresh_token = new_refresh_token
        user.refresh_token_expires = refresh_expires
        await self.db.flush()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user)
        )
    
    async def logout(self, user_id: int) -> bool:
        """Logout user by invalidating refresh token"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.refresh_token = None
        user.refresh_token_expires = None
        await self.db.flush()
        return True
    
    async def update_user(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """Update user profile"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def convert_guest_to_user(
        self, 
        guest_user_id: int, 
        user_data: UserCreate
    ) -> Optional[User]:
        """Convert a guest user to a full user account"""
        user = await self.get_user_by_id(guest_user_id)
        if not user or user.role != UserRole.GUEST:
            return None
        
        # Check if email is available
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")
        
        # Update user
        user.email = user_data.email.lower()
        user.hashed_password = self.hash_password(user_data.password)
        user.name = user_data.name
        user.school = user_data.school
        user.timezone = user_data.timezone
        user.role = UserRole.STANDARD
        user.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
