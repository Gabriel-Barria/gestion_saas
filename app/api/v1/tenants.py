import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import TenantServiceDep
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/projects/{project_id}/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    project_id: uuid.UUID,
    data: TenantCreate,
    service: TenantServiceDep,
):
    """
    Create a new tenant for a project.

    If the project uses schema isolation, a new PostgreSQL schema will be created.
    """
    return await service.create(project_id, data)


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    project_id: uuid.UUID,
    service: TenantServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List all tenants for a project."""
    return await service.get_all_by_project(project_id, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    service: TenantServiceDep,
):
    """Get a tenant by ID."""
    tenant = await service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    service: TenantServiceDep,
):
    """Update a tenant."""
    tenant = await service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")
    return await service.update(tenant_id, data)


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    service: TenantServiceDep,
):
    """
    Delete a tenant.

    If the tenant uses schema isolation, the PostgreSQL schema will be dropped.
    """
    tenant = await service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")
    await service.delete(tenant_id)
