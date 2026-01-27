import uuid
from pydantic import BaseModel, Field, EmailStr


class TokenRequest(BaseModel):
    """Request for token using API Key authentication."""
    email: EmailStr
    password: str
    tenant_slug: str


class OAuthTokenRequest(BaseModel):
    """Request for token using OAuth2 client credentials."""
    grant_type: str = Field(..., pattern="^(password|refresh_token)$")
    client_id: str
    client_secret: str
    username: EmailStr | None = None  # Required for grant_type=password
    password: str | None = None  # Required for grant_type=password
    tenant: str | None = None  # Tenant slug
    refresh_token: str | None = None  # Required for grant_type=refresh_token


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class TokenValidationRequest(BaseModel):
    """Request to validate a token."""
    token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    user_id: uuid.UUID | None = None
    email: str | None = None
    tenant_id: uuid.UUID | None = None
    tenant_slug: str | None = None
    project_id: uuid.UUID | None = None
    roles: list[str] = Field(default_factory=list)
    message: str | None = None


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user_id
    email: str
    tenant_id: str
    tenant_slug: str
    project_id: str
    roles: list[str] = Field(default_factory=list)
    exp: int
    iat: int
