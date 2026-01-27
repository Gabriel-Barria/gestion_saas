import uuid
from pydantic import BaseModel, Field, EmailStr

from app.schemas.membership import MembershipWithTenant


class JWTVerifyRequest(BaseModel):
    """Request to verify a JWT signature."""
    token: str


class JWTVerifyResponse(BaseModel):
    """Response from JWT verification."""
    valid: bool
    payload: dict | None = None  # Decoded payload if valid
    error: str | None = None


class ProjectInfoResponse(BaseModel):
    """Project info for SaaS clients (includes JWT secret for signing)."""
    id: uuid.UUID
    name: str
    slug: str
    tenant_strategy: str
    jwt_secret: str  # For signing JWTs
    jwt_algorithm: str
    jwt_expiration_minutes: int

    model_config = {"from_attributes": True}


class TenantInfoResponse(BaseModel):
    """Tenant info for SaaS clients."""
    id: uuid.UUID
    name: str
    slug: str
    schema_name: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


# === Global Auth Schemas ===

class RegisterRequest(BaseModel):
    """Request to register a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    """Response after successful registration."""
    id: uuid.UUID
    email: str
    full_name: str
    message: str = "User registered successfully"

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Request to login (global login - returns user + memberships)."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response from global login - includes user info and available memberships."""
    user_id: uuid.UUID
    email: str
    full_name: str
    memberships: list[MembershipWithTenant]


class LoginTenantRequest(BaseModel):
    """Request to login to a specific tenant."""
    email: EmailStr
    password: str
    tenant_id: uuid.UUID


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str
