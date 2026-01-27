from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.project import ProjectService
from app.services.tenant import TenantService
from app.services.user import UserService
from app.services.auth import AuthService
from app.core.exceptions import UnauthorizedError


async def get_project_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectService:
    return ProjectService(db)


async def get_tenant_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantService:
    return TenantService(db)


async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserService:
    return UserService(db)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuthService:
    return AuthService(db)


async def get_api_key(
    x_api_key: Annotated[str | None, Header()] = None
) -> str:
    """Extract API key from header."""
    if not x_api_key:
        raise UnauthorizedError("API key is required")
    return x_api_key


# Type aliases for dependency injection
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TenantServiceDep = Annotated[TenantService, Depends(get_tenant_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ApiKeyDep = Annotated[str, Depends(get_api_key)]
