from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import AuthServiceDep, ApiKeyDep
from app.schemas.auth import (
    JWTVerifyRequest,
    JWTVerifyResponse,
    ProjectInfoResponse,
    TenantInfoResponse,
)

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
