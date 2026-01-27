import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from app.schemas.user import UserBrief


class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str] = Field(default_factory=list)


class MembershipUpdate(BaseModel):
    roles: list[str] | None = None
    is_active: bool | None = None


class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MembershipWithUser(MembershipResponse):
    """Membership with user details (for listing tenant members)."""
    user: UserBrief


class MembershipWithTenant(BaseModel):
    """Membership with tenant details (for listing user's memberships)."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    project_id: uuid.UUID
    project_name: str
    roles: list[str]
    is_active: bool

    model_config = {"from_attributes": True}


# Invitation schemas
class InvitationCreate(BaseModel):
    email: EmailStr
    roles: list[str] = Field(default_factory=list)
    expires_in_hours: int = Field(default=48, ge=1, le=168)  # 1 hour to 7 days


class InvitationResponse(BaseModel):
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID
    roles: list[str]
    token: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationAccept(BaseModel):
    token: str
    password: str | None = Field(None, min_length=8, max_length=128)
    full_name: str | None = Field(None, min_length=1, max_length=255)


class InvitationInfo(BaseModel):
    """Public info about an invitation (without sensitive data)."""
    email: str
    tenant_name: str
    project_name: str
    roles: list[str]
    expires_at: datetime
    user_exists: bool  # Whether the user already has an account

    model_config = {"from_attributes": True}
