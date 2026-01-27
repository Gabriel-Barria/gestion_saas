import uuid
from slugify import slugify

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, TenantStrategy
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.security import (
    generate_api_key,
    generate_client_id,
    generate_client_secret,
    generate_jwt_secret,
    hash_password,
)
from app.core.exceptions import NotFoundError, ConflictError


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProjectCreate) -> tuple[Project, dict[str, str]]:
        """
        Create a new project with auto-generated credentials.
        Returns the project and a dict with plain-text credentials (shown only once).
        """
        slug = slugify(data.name)

        # Check if slug already exists
        existing = await self.get_by_slug(slug)
        if existing:
            # Append a unique suffix
            slug = f"{slug}-{uuid.uuid4().hex[:8]}"

        # Generate credentials
        api_key = generate_api_key()
        client_id = generate_client_id()
        client_secret = generate_client_secret()
        jwt_secret = generate_jwt_secret()

        project = Project(
            name=data.name,
            slug=slug,
            tenant_strategy=data.tenant_strategy,
            api_key_hash=hash_password(api_key),
            client_id=client_id,
            client_secret_hash=hash_password(client_secret),
            jwt_secret=jwt_secret,
        )

        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        credentials = {
            "api_key": api_key,
            "client_id": client_id,
            "client_secret": client_secret,
            "jwt_secret": jwt_secret,
        }

        return project, credentials

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Get a project by ID."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Project | None:
        """Get a project by slug."""
        result = await self.db.execute(
            select(Project).where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_client_id(self, client_id: str) -> Project | None:
        """Get a project by client_id."""
        result = await self.db.execute(
            select(Project).where(Project.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Project]:
        """Get all projects with pagination."""
        result = await self.db.execute(
            select(Project)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_tenants(self, project_id: uuid.UUID) -> Project | None:
        """Get a project with its tenants loaded."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.tenants))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, project_id: uuid.UUID, data: ProjectUpdate
    ) -> Project:
        """Update a project."""
        project = await self.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: uuid.UUID) -> None:
        """Delete a project."""
        project = await self.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        await self.db.delete(project)
        await self.db.commit()

    async def regenerate_api_key(self, project_id: uuid.UUID) -> str:
        """Regenerate API key for a project. Returns the new plain-text key."""
        project = await self.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        new_api_key = generate_api_key()
        project.api_key_hash = hash_password(new_api_key)

        await self.db.commit()
        return new_api_key

    async def regenerate_client_secret(self, project_id: uuid.UUID) -> str:
        """Regenerate client secret for a project. Returns the new plain-text secret."""
        project = await self.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        new_secret = generate_client_secret()
        project.client_secret_hash = hash_password(new_secret)

        await self.db.commit()
        return new_secret
