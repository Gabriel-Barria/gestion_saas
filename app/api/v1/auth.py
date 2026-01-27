from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import AuthServiceDep, ApiKeyDep
from app.schemas.auth import (
    TokenRequest,
    OAuthTokenRequest,
    TokenResponse,
    TokenValidationRequest,
    TokenValidationResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token", response_model=TokenResponse)
async def get_token_with_api_key(
    data: TokenRequest,
    api_key: ApiKeyDep,
    service: AuthServiceDep,
):
    """
    Get an access token using API Key authentication.

    The API key must be sent in the X-API-Key header.
    Provide email, password, and tenant_slug in the request body.
    """
    return await service.authenticate_with_api_key(api_key, data)


@router.post("/oauth/token", response_model=TokenResponse)
async def get_token_oauth(
    data: OAuthTokenRequest,
    service: AuthServiceDep,
):
    """
    Get an access token using OAuth2 client credentials.

    Supported grant types:
    - `password`: Exchange username/password for tokens. Requires: username, password, tenant
    - `refresh_token`: Exchange a refresh token for new tokens. Requires: refresh_token
    """
    return await service.authenticate_with_oauth(data)


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(
    data: TokenValidationRequest,
    api_key: ApiKeyDep,
    service: AuthServiceDep,
):
    """
    Validate a JWT token.

    The API key must be sent in the X-API-Key header to identify the project.
    Returns token validity and decoded user information.
    """
    return await service.validate_token(data.token, api_key)


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token_bearer(
    api_key: ApiKeyDep,
    service: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
):
    """
    Validate a JWT token from Authorization header.

    The API key must be sent in the X-API-Key header.
    The JWT must be sent in the Authorization header as: Bearer <token>
    """
    if not authorization:
        return TokenValidationResponse(
            valid=False, message="Authorization header is required"
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return TokenValidationResponse(
            valid=False, message="Invalid Authorization header format"
        )

    token = parts[1]
    return await service.validate_token(token, api_key)
