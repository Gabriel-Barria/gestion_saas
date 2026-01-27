import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    TokenRequest,
    OAuthTokenRequest,
    TokenResponse,
    TokenValidationResponse,
)
from app.core.security import (
    verify_api_key,
    verify_client_secret,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.core.exceptions import UnauthorizedError, NotFoundError


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_with_api_key(
        self, api_key: str, data: TokenRequest
    ) -> TokenResponse:
        """
        Authenticate a user using API Key.
        The API key identifies the project, then we authenticate the user.
        """
        # Find project by API key (need to check all projects)
        project = await self._find_project_by_api_key(api_key)
        if not project:
            raise UnauthorizedError("Invalid API key")

        if not project.is_active:
            raise UnauthorizedError("Project is inactive")

        # Find tenant
        tenant = await self._get_tenant_by_project_and_slug(
            project.id, data.tenant_slug
        )
        if not tenant:
            raise NotFoundError("Tenant not found")

        if not tenant.is_active:
            raise UnauthorizedError("Tenant is inactive")

        # Authenticate user
        user = await self._authenticate_user(tenant.id, data.email, data.password)
        if not user:
            raise UnauthorizedError("Invalid credentials")

        # Create tokens
        return self._create_token_response(user, tenant, project)

    async def authenticate_with_oauth(
        self, data: OAuthTokenRequest
    ) -> TokenResponse:
        """
        Authenticate using OAuth2 client credentials flow.
        """
        # Find project by client_id
        project = await self._get_project_by_client_id(data.client_id)
        if not project:
            raise UnauthorizedError("Invalid client credentials")

        # Verify client secret
        if not verify_client_secret(data.client_secret, project.client_secret_hash):
            raise UnauthorizedError("Invalid client credentials")

        if not project.is_active:
            raise UnauthorizedError("Project is inactive")

        if data.grant_type == "password":
            if not data.username or not data.password or not data.tenant:
                raise UnauthorizedError("Missing required fields for password grant")

            # Find tenant
            tenant = await self._get_tenant_by_project_and_slug(project.id, data.tenant)
            if not tenant:
                raise NotFoundError("Tenant not found")

            if not tenant.is_active:
                raise UnauthorizedError("Tenant is inactive")

            # Authenticate user
            user = await self._authenticate_user(
                tenant.id, data.username, data.password
            )
            if not user:
                raise UnauthorizedError("Invalid credentials")

            return self._create_token_response(user, tenant, project, include_refresh=True)

        elif data.grant_type == "refresh_token":
            if not data.refresh_token:
                raise UnauthorizedError("Missing refresh token")

            # Decode refresh token
            payload = decode_token(
                data.refresh_token, project.jwt_secret, project.jwt_algorithm
            )
            if not payload:
                raise UnauthorizedError("Invalid refresh token")

            if payload.get("type") != "refresh":
                raise UnauthorizedError("Invalid token type")

            # Get user and tenant
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")

            user = await self._get_user_by_id(uuid.UUID(user_id))
            tenant = await self._get_tenant_by_id(uuid.UUID(tenant_id))

            if not user or not tenant:
                raise UnauthorizedError("Invalid refresh token")

            if not user.is_active or not tenant.is_active:
                raise UnauthorizedError("User or tenant is inactive")

            return self._create_token_response(user, tenant, project, include_refresh=True)

        raise UnauthorizedError("Unsupported grant type")

    async def validate_token(
        self, token: str, api_key: str
    ) -> TokenValidationResponse:
        """
        Validate a JWT token.
        The API key is used to identify the project and get the JWT secret.
        """
        # Find project by API key
        project = await self._find_project_by_api_key(api_key)
        if not project:
            return TokenValidationResponse(valid=False, message="Invalid API key")

        # Decode token
        payload = decode_token(token, project.jwt_secret, project.jwt_algorithm)
        if not payload:
            return TokenValidationResponse(valid=False, message="Invalid or expired token")

        return TokenValidationResponse(
            valid=True,
            user_id=uuid.UUID(payload["sub"]),
            email=payload["email"],
            tenant_id=uuid.UUID(payload["tenant_id"]),
            tenant_slug=payload["tenant_slug"],
            project_id=uuid.UUID(payload["project_id"]),
            roles=payload.get("roles", []),
        )

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

    async def _get_tenant_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _authenticate_user(
        self, tenant_id: uuid.UUID, email: str, password: str
    ) -> User | None:
        """Authenticate a user by email and password."""
        result = await self.db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == email,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def _create_token_response(
        self,
        user: User,
        tenant: Tenant,
        project: Project,
        include_refresh: bool = False,
    ) -> TokenResponse:
        """Create a token response for an authenticated user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "project_id": str(project.id),
            "roles": user.roles,
        }

        access_token = create_access_token(
            data=token_data,
            secret_key=project.jwt_secret,
            algorithm=project.jwt_algorithm,
            expires_delta=timedelta(minutes=project.jwt_expiration_minutes),
        )

        response = TokenResponse(
            access_token=access_token,
            expires_in=project.jwt_expiration_minutes * 60,
        )

        if include_refresh:
            response.refresh_token = create_refresh_token(
                data=token_data,
                secret_key=project.jwt_secret,
                algorithm=project.jwt_algorithm,
            )

        return response
