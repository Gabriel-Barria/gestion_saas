import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.tenant import Tenant
from app.schemas.auth import (
    JWTVerifyRequest,
    JWTVerifyResponse,
    ProjectInfoResponse,
    TenantInfoResponse,
)
from app.core.security import (
    verify_api_key,
    verify_client_secret,
    decode_token,
)
from app.core.exceptions import UnauthorizedError, NotFoundError


class AuthService:
    """
    Service for authentication utilities.

    This service does NOT handle user authentication (that's the responsibility
    of each SaaS project). It provides:
    - JWT signature verification
    - Project info (including JWT secret for signing)
    - Tenant info lookup
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_by_api_key(self, api_key: str) -> Project:
        """
        Get project info by API key.
        Returns the project including JWT secret for signing tokens.
        """
        project = await self._find_project_by_api_key(api_key)
        if not project:
            raise UnauthorizedError("Invalid API key")
        if not project.is_active:
            raise UnauthorizedError("Project is inactive")
        return project

    async def get_project_by_client_credentials(
        self, client_id: str, client_secret: str
    ) -> Project:
        """
        Get project info by client credentials (OAuth2 style).
        """
        project = await self._get_project_by_client_id(client_id)
        if not project:
            raise UnauthorizedError("Invalid client credentials")
        if not verify_client_secret(client_secret, project.client_secret_hash):
            raise UnauthorizedError("Invalid client credentials")
        if not project.is_active:
            raise UnauthorizedError("Project is inactive")
        return project

    async def get_tenant_info(
        self, api_key: str, tenant_slug: str
    ) -> TenantInfoResponse:
        """
        Get tenant info by slug.
        Requires API key to identify the project.
        """
        project = await self.get_project_by_api_key(api_key)

        tenant = await self._get_tenant_by_project_and_slug(project.id, tenant_slug)
        if not tenant:
            raise NotFoundError("Tenant not found")

        return TenantInfoResponse.model_validate(tenant)

    async def verify_jwt(self, api_key: str, token: str) -> JWTVerifyResponse:
        """
        Verify a JWT signature.
        The API key identifies the project to get the JWT secret.

        This only verifies the signature is valid - it does NOT verify
        the user exists (that's the SaaS project's responsibility).
        """
        try:
            project = await self.get_project_by_api_key(api_key)
        except UnauthorizedError as e:
            return JWTVerifyResponse(valid=False, error=str(e))

        payload = decode_token(token, project.jwt_secret, project.jwt_algorithm)
        if not payload:
            return JWTVerifyResponse(valid=False, error="Invalid or expired token")

        return JWTVerifyResponse(valid=True, payload=payload)

    async def _find_project_by_api_key(self, api_key: str) -> Project | None:
        """Find a project by verifying the API key against all projects."""
        result = await self.db.execute(select(Project))
        projects = result.scalars().all()

        for project in projects:
            if verify_api_key(api_key, project.api_key_hash):
                return project
        return None

    async def _get_project_by_client_id(self, client_id: str) -> Project | None:
        """Get a project by client_id."""
        result = await self.db.execute(
            select(Project).where(Project.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def _get_tenant_by_project_and_slug(
        self, project_id: uuid.UUID, slug: str
    ) -> Tenant | None:
        """Get a tenant by project ID and slug."""
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.project_id == project_id,
                Tenant.slug == slug,
            )
        )
        return result.scalar_one_or_none()
