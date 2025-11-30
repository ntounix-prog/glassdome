"""
Authentication Service

JWT token generation, password hashing, user operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from glassdome.auth.models import User, UserRole, ROLE_LEVELS
from glassdome.auth.schemas import TokenData, UserCreate

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_jwt_config():
    """Get JWT configuration (from Vault or settings)."""
    from glassdome.auth.vault_integration import get_auth_config
    return get_auth_config()


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    config = _get_jwt_config()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config["expire_minutes"])
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config["jwt_secret"], algorithm=config["algorithm"])
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    config = _get_jwt_config()
    try:
        payload = jwt.decode(token, config["jwt_secret"], algorithms=[config["algorithm"]])
        # JWT sub must be a string, convert back to int
        sub = payload.get("sub")
        user_id = int(sub) if sub else None
        username: str = payload.get("username")
        email: str = payload.get("email")
        role: str = payload.get("role")
        level: int = payload.get("level")
        
        if user_id is None:
            return None
        
        return TokenData(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            level=level
        )
    except JWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_username_or_email(session: AsyncSession, identifier: str) -> Optional[User]:
    """Get user by username OR email."""
    result = await session.execute(
        select(User).where(
            or_(User.username == identifier, User.email == identifier)
        )
    )
    return result.scalar_one_or_none()


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Authenticate user by username/email and password.
    
    Returns User if valid, None otherwise.
    """
    user = await get_user_by_username_or_email(session, username)
    
    if not user:
        logger.debug(f"User not found: {username}")
        return None
    
    if not user.is_active:
        logger.debug(f"User inactive: {username}")
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.debug(f"Invalid password for: {username}")
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await session.commit()
    
    return user


async def create_user(
    session: AsyncSession,
    user_data: UserCreate,
    created_by: Optional[User] = None
) -> User:
    """
    Create a new user.
    
    Args:
        session: Database session
        user_data: User creation data
        created_by: User creating this user (for audit)
        
    Returns:
        Created User
        
    Raises:
        ValueError: If email or username already exists
    """
    # Check if email exists
    existing = await get_user_by_email(session, user_data.email)
    if existing:
        raise ValueError(f"Email already registered: {user_data.email}")
    
    # Check if username exists
    existing = await get_user_by_username(session, user_data.username)
    if existing:
        raise ValueError(f"Username already taken: {user_data.username}")
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role.value,
        level=ROLE_LEVELS.get(user_data.role, 25),
        created_by_id=created_by.id if created_by else None,
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Created user: {user.username} ({user.role})")
    return user


async def update_user_password(
    session: AsyncSession,
    user: User,
    new_password: str
) -> User:
    """Update user password."""
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user


async def list_users(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> tuple[list[User], int]:
    """List users with pagination."""
    query = select(User)
    
    if active_only:
        query = query.where(User.is_active == True)
    
    # Get total count
    from sqlalchemy import func
    count_result = await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True) if active_only 
        else select(func.count()).select_from(User)
    )
    total = count_result.scalar()
    
    # Get users
    result = await session.execute(
        query.offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    
    return list(users), total


async def create_initial_admin(session: AsyncSession) -> Optional[User]:
    """
    Create initial admin user if no users exist.
    
    Returns created admin or None if users already exist.
    """
    # Check if any users exist
    result = await session.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return None
    
    # Create admin user
    from glassdome.auth.schemas import UserCreate
    admin_data = UserCreate(
        email="admin@glassdome.local",
        username="admin",
        password="changeme123!",  # Force change on first login
        full_name="System Administrator",
        role=UserRole.ADMIN,
    )
    
    admin = await create_user(session, admin_data)
    admin.is_superuser = True
    await session.commit()
    
    logger.warning("=" * 60)
    logger.warning("CREATED INITIAL ADMIN USER")
    logger.warning("  Username: admin")
    logger.warning("  Password: changeme123!")
    logger.warning("  *** CHANGE THIS PASSWORD IMMEDIATELY ***")
    logger.warning("=" * 60)
    
    return admin

