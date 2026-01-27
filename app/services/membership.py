import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.tenant import Tenant
from app.models.membership import Membership
from app.models.invitation import Invitation
from app.schemas.membership import (
    MembershipCreate,
    MembershipUpdate,
    InvitationCreate,
    MembershipWithTenant,
)
from app.core.security import hash_password
from app.core.exceptions import NotFoundError, BadRequestError


class MembershipService:
    """Service for membership and invitation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Membership Methods ===

    async def get_by_id(self, membership_id: uuid.UUID) -> Membership | None:
        """Get a membership by ID."""
        result = await self.db.execute(
            select(Membership).where(Membership.id == membership_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_tenant(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Membership | None:
        """Get a membership by user and tenant."""
        result = await self.db.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_memberships(
        self, user_id: uuid.UUID
    ) -> list[MembershipWithTenant]:
        """Get all memberships for a user with tenant and project details."""
        result = await self.db.execute(
            select(Membership)
            .options(
                selectinload(Membership.tenant).selectinload(Tenant.project)
            )
            .where(Membership.user_id == user_id, Membership.is_active == True)
            .order_by(Membership.created_at.desc())
        )
        memberships = result.scalars().all()

        return [
            MembershipWithTenant(
                id=m.id,
                tenant_id=m.tenant_id,
                tenant_name=m.tenant.name,
                tenant_slug=m.tenant.slug,
                project_id=m.tenant.project_id,
                project_name=m.tenant.project.name,
                roles=m.roles,
                is_active=m.is_active,
            )
            for m in memberships
        ]

    async def get_tenant_members(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Membership]:
        """Get all members of a tenant with user details."""
        result = await self.db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.tenant_id == tenant_id)
            .order_by(Membership.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, data: MembershipCreate) -> Membership:
        """Create a new membership."""
        # Check if membership already exists
        existing = await self.get_by_user_and_tenant(data.user_id, data.tenant_id)
        if existing:
            raise BadRequestError("User is already a member of this tenant")

        # Verify user exists
        user = await self._get_user(data.user_id)
        if not user:
            raise NotFoundError("User not found")

        # Verify tenant exists
        tenant = await self._get_tenant(data.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        membership = Membership(
            user_id=data.user_id,
            tenant_id=data.tenant_id,
            roles=data.roles or [],
        )

        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def update(
        self, membership_id: uuid.UUID, data: MembershipUpdate
    ) -> Membership:
        """Update a membership."""
        membership = await self.get_by_id(membership_id)
        if not membership:
            raise NotFoundError("Membership not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(membership, field, value)

        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def delete(self, membership_id: uuid.UUID) -> None:
        """Delete a membership."""
        membership = await self.get_by_id(membership_id)
        if not membership:
            raise NotFoundError("Membership not found")

        await self.db.delete(membership)
        await self.db.commit()

    # === Invitation Methods ===

    async def get_invitation_by_id(
        self, invitation_id: uuid.UUID
    ) -> Invitation | None:
        """Get an invitation by ID."""
        result = await self.db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_invitation_by_token(self, token: str) -> Invitation | None:
        """Get an invitation by token."""
        result = await self.db.execute(
            select(Invitation)
            .options(selectinload(Invitation.tenant).selectinload(Tenant.project))
            .where(Invitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_pending_invitation(
        self, email: str, tenant_id: uuid.UUID
    ) -> Invitation | None:
        """Get a pending invitation for an email and tenant."""
        result = await self.db.execute(
            select(Invitation).where(
                Invitation.email == email.lower(),
                Invitation.tenant_id == tenant_id,
                Invitation.used_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_tenant_invitations(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Invitation]:
        """Get all pending invitations for a tenant."""
        result = await self.db.execute(
            select(Invitation)
            .where(
                Invitation.tenant_id == tenant_id,
                Invitation.used_at.is_(None),
            )
            .order_by(Invitation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_invitation(
        self, tenant_id: uuid.UUID, data: InvitationCreate
    ) -> Invitation:
        """Create a new invitation."""
        # Verify tenant exists
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        # Check if user already has membership
        user = await self._get_user_by_email(data.email)
        if user:
            existing = await self.get_by_user_and_tenant(user.id, tenant_id)
            if existing:
                raise BadRequestError("User is already a member of this tenant")

        # Check for pending invitation
        pending = await self.get_pending_invitation(data.email, tenant_id)
        if pending:
            raise BadRequestError("An invitation already exists for this email")

        invitation = Invitation(
            email=data.email.lower(),
            tenant_id=tenant_id,
            roles=data.roles or [],
            expires_at=datetime.utcnow() + timedelta(hours=data.expires_in_hours),
        )

        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def accept_invitation(
        self,
        token: str,
        password: str | None = None,
        full_name: str | None = None,
    ) -> tuple[User, Membership]:
        """
        Accept an invitation.

        Returns the user and the created membership.
        If user doesn't exist, password and full_name are required.
        """
        invitation = await self.get_invitation_by_token(token)
        if not invitation:
            raise NotFoundError("Invitation not found")

        if invitation.is_used:
            raise BadRequestError("Invitation has already been used")

        if invitation.is_expired:
            raise BadRequestError("Invitation has expired")

        # Check if user exists
        user = await self._get_user_by_email(invitation.email)

        if not user:
            # Create new user
            if not password:
                raise BadRequestError("Password is required for new users")
            if not full_name:
                raise BadRequestError("Full name is required for new users")

            user = User(
                email=invitation.email,
                password_hash=hash_password(password),
                full_name=full_name,
                email_verified=True,
            )
            self.db.add(user)
            await self.db.flush()  # Get the user ID

        # Create membership
        membership = Membership(
            user_id=user.id,
            tenant_id=invitation.tenant_id,
            roles=invitation.roles,
        )
        self.db.add(membership)

        # Mark invitation as used
        invitation.used_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(membership)

        return user, membership

    async def delete_invitation(self, invitation_id: uuid.UUID) -> None:
        """Delete an invitation."""
        invitation = await self.get_invitation_by_id(invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found")

        await self.db.delete(invitation)
        await self.db.commit()

    # === Helper Methods ===

    async def _get_user(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        result = await self.db.execute(
            select(User).where(User.email.ilike(email))
        )
        return result.scalar_one_or_none()

    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
