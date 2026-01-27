import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password
from app.core.exceptions import NotFoundError, BadRequestError


class UserService:
    """Service for user management (global identity)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(User.email.ilike(email))
        )
        return result.scalar_one_or_none()

    async def get_with_memberships(self, user_id: uuid.UUID) -> User | None:
        """Get a user with memberships loaded."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.memberships))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.get_by_email(data.email)
        if existing:
            raise BadRequestError("Email already registered")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            email_verified=True,  # Auto-verify for MVP
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        """Update a user."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> User:
        """Update a user's password."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_password(self, user_id: uuid.UUID, new_password: str) -> User:
        """Set a user's password (for invitation acceptance)."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def verify_credentials(self, email: str, password: str) -> User | None:
        """Verify user credentials. Returns user if valid, None otherwise."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        """Delete a user."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        await self.db.delete(user)
        await self.db.commit()
