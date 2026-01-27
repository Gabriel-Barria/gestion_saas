import uuid
from slugify import slugify

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.database import create_schema, drop_schema
from app.core.exceptions import NotFoundError, BadRequestError


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, project_id: uuid.UUID, data: TenantCreate
    ) -> Tenant:
        """Create a new tenant for a project."""
        # Get the project to check tenant strategy
        project = await self._get_project(project_id)
        if not project:
            raise NotFoundError("Project not found")

        slug = slugify(data.name)

        # Check if slug already exists in this project
        existing = await self.get_by_project_and_slug(project_id, slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:8]}"

        schema_name = None
        if project.tenant_strategy == "schema":
            # Create a unique schema name
            schema_name = f"tenant_{project.slug}_{slug}".replace("-", "_")
            await create_schema(schema_name)

        tenant = Tenant(
            project_id=project_id,
            name=data.name,
            slug=slug,
            schema_name=schema_name,
        )

        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def _get_project(self, project_id: uuid.UUID) -> Project | None:
        """Get a project by ID."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project_and_slug(
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

    async def get_all_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Tenant]:
        """Get all tenants for a project."""
        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.project_id == project_id)
            .order_by(Tenant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_users(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant with its users loaded."""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.users))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_with_project(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Get a tenant with its project loaded."""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.project))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, tenant_id: uuid.UUID, data: TenantUpdate
    ) -> Tenant:
        """Update a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        update_data = data.model_dump(exclude_unset=True)

        # Don't allow changing name if it would affect schema name
        if "name" in update_data and tenant.schema_name:
            raise BadRequestError(
                "Cannot change tenant name when using schema isolation"
            )

        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def delete(self, tenant_id: uuid.UUID) -> None:
        """Delete a tenant and its schema if applicable."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        # Drop the schema if it exists
        if tenant.schema_name:
            await drop_schema(tenant.schema_name)

        await self.db.delete(tenant)
        await self.db.commit()
