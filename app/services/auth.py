import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.models.membership import Membership
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
)
from app.schemas.membership import MembershipWithTenant
from app.core.security import (
    verify_api_key,
    verify_client_secret,
    verify_password,
    hash_password,
    decode_token,
    create_access_token,
    create_refresh_token,
)
from app.core.exceptions import UnauthorizedError, NotFoundError, BadRequestError
from app.config import settings


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

    # === Global Authentication Methods ===

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """Register a new user (global identity)."""
        # Check if email already exists
        existing = await self._get_user_by_email(data.email)
        if existing:
            raise BadRequestError("Email already registered")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            email_verified=True,  # Auto-verify for MVP
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return RegisterResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
        )

    async def login_global(self, data: LoginRequest) -> LoginResponse:
        """
        Global login - validates credentials and returns user with memberships.
        This allows the user to select which tenant to access.
        """
        user = await self._verify_credentials(data.email, data.password)
        if not user:
            raise UnauthorizedError("Invalid email or password")

        memberships = await self._get_user_memberships(user.id)

        return LoginResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            memberships=memberships,
        )

    async def login_tenant(self, data: LoginTenantRequest) -> TokenResponse:
        """
        Login to a specific tenant - validates credentials and membership,
        then returns JWT tokens.
        """
        user = await self._verify_credentials(data.email, data.password)
        if not user:
            raise UnauthorizedError("Invalid email or password")

        # Check membership
        membership = await self._get_membership(user.id, data.tenant_id)
        if not membership:
            raise UnauthorizedError("User is not a member of this tenant")
        if not membership.is_active:
            raise UnauthorizedError("Membership is inactive")

        # Get tenant with project for JWT secret
        tenant = await self._get_tenant_with_project(data.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        if not tenant.is_active:
            raise UnauthorizedError("Tenant is inactive")
        if not tenant.project.is_active:
            raise UnauthorizedError("Project is inactive")

        # Generate tokens
        return self._generate_tokens(
            user=user,
            tenant=tenant,
            membership=membership,
        )

    async def refresh_token(
        self, refresh_token: str, api_key: str | None = None
    ) -> TokenResponse:
        """
        Refresh access token using a refresh token.
        Optionally validates API key for additional security.
        """
        # If API key provided, validate it first
        project = None
        if api_key:
            project = await self._find_project_by_api_key(api_key)
            if not project:
                raise UnauthorizedError("Invalid API key")

        # Decode refresh token to get user/tenant info
        # We need to try decoding with different project secrets
        # since we don't know which project issued it initially
        payload = None

        if project:
            # Try with the specific project's secret
            payload = decode_token(
                refresh_token,
                project.jwt_secret,
                project.jwt_algorithm,
            )
        else:
            # Try all active projects (less efficient but necessary without API key)
            result = await self.db.execute(
                select(Project).where(Project.is_active == True)
            )
            projects = result.scalars().all()
            for p in projects:
                payload = decode_token(refresh_token, p.jwt_secret, p.jwt_algorithm)
                if payload:
                    project = p
                    break

        if not payload:
            raise UnauthorizedError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        # Validate user and membership still exist and are active
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])

        user = await self._get_user(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        membership = await self._get_membership(user_id, tenant_id)
        if not membership or not membership.is_active:
            raise UnauthorizedError("Membership not found or inactive")

        tenant = await self._get_tenant_with_project(tenant_id)
        if not tenant or not tenant.is_active or not tenant.project.is_active:
            raise UnauthorizedError("Tenant or project inactive")

        return self._generate_tokens(
            user=user,
            tenant=tenant,
            membership=membership,
        )

    def _generate_tokens(
        self,
        user: User,
        tenant: Tenant,
        membership: Membership,
    ) -> TokenResponse:
        """Generate access and refresh tokens."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(tenant.id),
            "project_id": str(tenant.project_id),
            "roles": membership.roles,
        }

        expires_delta = timedelta(minutes=tenant.project.jwt_expiration_minutes)

        access_token = create_access_token(
            data={**token_data, "type": "access"},
            secret_key=tenant.project.jwt_secret,
            algorithm=tenant.project.jwt_algorithm,
            expires_delta=expires_delta,
        )

        refresh_token = create_refresh_token(
            data=token_data,
            secret_key=tenant.project.jwt_secret,
            algorithm=tenant.project.jwt_algorithm,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(expires_delta.total_seconds()),
        )

    # === Helper Methods for Global Auth ===

    async def _get_user(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get a user by email (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(User.email.ilike(email))
        )
        return result.scalar_one_or_none()

    async def _verify_credentials(self, email: str, password: str) -> User | None:
        """Verify user credentials."""
        user = await self._get_user_by_email(email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def _get_membership(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Membership | None:
        """Get a membership by user and tenant."""
        result = await self.db.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_user_memberships(
        self, user_id: uuid.UUID
    ) -> list[MembershipWithTenant]:
        """Get all active memberships for a user."""
        result = await self.db.execute(
            select(Membership)
            .options(
                selectinload(Membership.tenant).selectinload(Tenant.project)
            )
            .where(Membership.user_id == user_id, Membership.is_active == True)
        )
        memberships = result.scalars().all()

        return [
            MembershipWithTenant(
                id=m.id,
                tenant_id=m.tenant_id,
                tenant_name=m.tenant.name,
                tenant_slug=m.tenant.slug,
                project_id=m.tenant.project_id,
                project_name=m.tenant.project.name,
                roles=m.roles,
                is_active=m.is_active,
            )
            for m in memberships
        ]

    async def _get_tenant_with_project(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant with its project loaded."""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.project))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
