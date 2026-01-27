import uuid
from pydantic import BaseModel, Field


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
