from typing import Annotated
import uuid

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.project import ProjectService
from app.services.tenant import TenantService
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.membership import MembershipService
from app.models.user import User
from app.models.project import Project
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError


async def get_project_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectService:
    return ProjectService(db)


async def get_tenant_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantService:
    return TenantService(db)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuthService:
    return AuthService(db)


async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserService:
    return UserService(db)


async def get_membership_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> MembershipService:
    return MembershipService(db)


async def get_api_key(
    x_api_key: Annotated[str | None, Header()] = None
) -> str:
    """Extract API key from header."""
    if not x_api_key:
        raise UnauthorizedError("API key is required")
    return x_api_key


async def get_optional_api_key(
    x_api_key: Annotated[str | None, Header()] = None
) -> str | None:
    """Extract optional API key from header."""
    return x_api_key


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Get current user from JWT token in Authorization header.

    This decodes the JWT and validates the user exists.
    Note: For full security, use get_current_user_for_tenant which also
    validates the tenant and membership.
    """
    if not authorization:
        raise UnauthorizedError("Authorization header is required")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid Authorization format. Use: Bearer <token>")

    token = parts[1]

    # Try to decode with all active projects (we need to find which one issued the token)
    result = await db.execute(
        select(Project).where(Project.is_active == True)
    )
    projects = result.scalars().all()

    payload = None
    for project in projects:
        payload = decode_token(token, project.jwt_secret, project.jwt_algorithm)
        if payload:
            break

    if not payload:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") == "refresh":
        raise UnauthorizedError("Cannot use refresh token for authentication")

    # Get the user
    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("User is inactive")

    return user


# Type aliases for dependency injection
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TenantServiceDep = Annotated[TenantService, Depends(get_tenant_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
ApiKeyDep = Annotated[str, Depends(get_api_key)]
OptionalApiKeyDep = Annotated[str | None, Depends(get_optional_api_key)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
