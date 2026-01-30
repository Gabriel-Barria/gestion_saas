from typing import Annotated

from fastapi import APIRouter, Header, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import AuthServiceDep, MembershipServiceDep, ApiKeyDep
from app.config import settings

limiter = Limiter(key_func=get_remote_address)
from app.schemas.auth import (
    JWTVerifyRequest,
    JWTVerifyResponse,
    ProjectInfoResponse,
    TenantInfoResponse,
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    LoginTenantRequest,
    TokenResponse,
    RefreshRequest,
)
from app.schemas.membership import InvitationAccept, InvitationInfo

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/project", response_model=ProjectInfoResponse)
async def get_project_info(
    api_key: ApiKeyDep,
    service: AuthServiceDep,
):
    """
    Get project information including JWT secret for signing tokens.

    **Use this endpoint to get your project's JWT configuration.**

    The API key must be sent in the `X-API-Key` header.

    Returns:
    - Project ID, name, slug
    - JWT secret (for signing tokens in your SaaS)
    - JWT algorithm and expiration settings
    """
    project = await service.get_project_by_api_key(api_key)
    return ProjectInfoResponse.model_validate(project)


@router.get("/tenant/{tenant_slug}", response_model=TenantInfoResponse)
async def get_tenant_info(
    tenant_slug: str,
    api_key: ApiKeyDep,
    service: AuthServiceDep,
):
    """
    Get tenant information by slug.

    **Use this endpoint to resolve a tenant slug to its ID and metadata.**

    The API key must be sent in the `X-API-Key` header to identify your project.

    Returns:
    - Tenant ID, name, slug
    - Schema name (if using schema isolation)
    - Active status
    """
    return await service.get_tenant_info(api_key, tenant_slug)


@router.post("/verify", response_model=JWTVerifyResponse)
async def verify_jwt(
    data: JWTVerifyRequest,
    api_key: ApiKeyDep,
    service: AuthServiceDep,
):
    """
    Verify a JWT signature.

    **Use this endpoint to verify tokens were signed with your project's secret.**

    The API key must be sent in the `X-API-Key` header to identify your project.

    This only verifies the signature is valid and the token is not expired.
    It does NOT verify the user exists (that's your SaaS's responsibility).

    Returns:
    - valid: boolean
    - payload: decoded JWT payload if valid
    - error: error message if invalid
    """
    return await service.verify_jwt(api_key, data.token)


@router.get("/verify", response_model=JWTVerifyResponse)
async def verify_jwt_bearer(
    api_key: ApiKeyDep,
    service: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
):
    """
    Verify a JWT from Authorization header.

    **Alternative to POST /verify - reads token from Authorization header.**

    Headers required:
    - `X-API-Key`: Your project's API key
    - `Authorization`: Bearer <token>
    """
    if not authorization:
        return JWTVerifyResponse(valid=False, error="Authorization header is required")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JWTVerifyResponse(valid=False, error="Invalid Authorization header format. Use: Bearer <token>")

    token = parts[1]
    return await service.verify_jwt(api_key, token)


# === Global Authentication Endpoints ===

@router.post("/register", response_model=RegisterResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    service: AuthServiceDep,
):
    """
    Register a new user (global identity).

    **This creates a user account without any tenant access.**

    To access a tenant, the user must either:
    - Be invited by a tenant admin
    - Self-register to a tenant (if the SaaS allows it)

    Returns:
    - User ID, email, and full name
    """
    return await service.register(data)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def login_global(
    request: Request,
    data: LoginRequest,
    service: AuthServiceDep,
):
    """
    Global login - authenticate user and get available tenants.

    **This validates credentials and returns user info with all memberships.**

    Use this to let users select which tenant they want to access,
    then call `/auth/login/tenant` to get JWT tokens for that tenant.

    Returns:
    - User ID, email, full name
    - List of memberships (tenants the user can access)
    """
    return await service.login_global(data)


@router.post("/login/tenant", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def login_tenant(
    request: Request,
    data: LoginTenantRequest,
    service: AuthServiceDep,
):
    """
    Login to a specific tenant - get JWT tokens.

    **This validates credentials and membership, then returns JWT tokens.**

    The access token includes:
    - user ID (sub)
    - email
    - tenant_id
    - project_id
    - roles

    Returns:
    - access_token: Short-lived token for API calls
    - refresh_token: Long-lived token to get new access tokens
    - expires_in: Access token expiration in seconds
    """
    return await service.login_tenant(data)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def refresh_token(
    request: Request,
    data: RefreshRequest,
    service: AuthServiceDep,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """
    Refresh access token using a refresh token.

    **Use this to get a new access token without re-authenticating.**

    Optionally provide `X-API-Key` header for additional security validation.

    Returns:
    - New access_token and refresh_token
    """
    return await service.refresh_token(data.refresh_token, x_api_key)


@router.get("/invitations/{token}", response_model=InvitationInfo)
async def get_invitation_info(
    token: str,
    membership_service: MembershipServiceDep,
):
    """
    Get invitation details by token.

    **Use this to show invitation info before accepting.**

    Returns public info about the invitation (tenant name, roles, etc.)
    and whether the user already has an account.
    """
    from app.core.exceptions import NotFoundError, BadRequestError

    invitation = await membership_service.get_invitation_by_token(token)
    if not invitation:
        raise NotFoundError("Invitation not found")

    if invitation.is_used:
        raise BadRequestError("Invitation has already been used")

    if invitation.is_expired:
        raise BadRequestError("Invitation has expired")

    # Check if user exists
    user = await membership_service._get_user_by_email(invitation.email)

    return InvitationInfo(
        email=invitation.email,
        tenant_name=invitation.tenant.name,
        project_name=invitation.tenant.project.name,
        roles=invitation.roles,
        expires_at=invitation.expires_at,
        user_exists=user is not None,
    )


@router.post("/invitations/accept")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def accept_invitation(
    request: Request,
    data: InvitationAccept,
    membership_service: MembershipServiceDep,
):
    """
    Accept an invitation and join a tenant.

    **If the user doesn't exist, password and full_name are required.**

    This will:
    - Create the user account if needed (using provided password/name)
    - Create the membership to the tenant
    - Mark the invitation as used

    Returns:
    - User info and created membership
    """
    from app.schemas.user import UserResponse
    from app.schemas.membership import MembershipResponse

    user, membership = await membership_service.accept_invitation(
        token=data.token,
        password=data.password,
        full_name=data.full_name,
    )

    return {
        "user": UserResponse.model_validate(user),
        "membership": MembershipResponse.model_validate(membership),
        "message": "Invitation accepted successfully",
    }
