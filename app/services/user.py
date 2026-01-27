import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password
from app.core.exceptions import NotFoundError, ConflictError


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: UserCreate) -> User:
        """Create a new user for a tenant."""
        # Verify tenant exists
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        # Check if email already exists in this tenant
        existing = await self.get_by_tenant_and_email(tenant_id, data.email)
        if existing:
            raise ConflictError("User with this email already exists in this tenant")

        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            roles=data.roles,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tenant_and_email(
        self, tenant_id: uuid.UUID, email: str
    ) -> User | None:
        """Get a user by tenant ID and email."""
        result = await self.db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_tenant(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """Get all users for a tenant."""
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        """Update a user."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        update_data = data.model_dump(exclude_unset=True)

        # Hash password if provided
        if "password" in update_data:
            update_data["password_hash"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        """Delete a user."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        await self.db.delete(user)
        await self.db.commit()

    async def authenticate(
        self, tenant_id: uuid.UUID, email: str, password: str
    ) -> User | None:
        """Authenticate a user by email and password."""
        user = await self.get_by_tenant_and_email(tenant_id, email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
