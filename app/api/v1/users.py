import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import UserServiceDep, TenantServiceDep
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.exceptions import NotFoundError

router = APIRouter(
    prefix="/projects/{project_id}/tenants/{tenant_id}/users",
    tags=["users"],
)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    data: UserCreate,
    user_service: UserServiceDep,
    tenant_service: TenantServiceDep,
):
    """Create a new user for a tenant."""
    # Verify tenant belongs to project
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    return await user_service.create(tenant_id, data)


@router.get("", response_model=list[UserResponse])
async def list_users(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_service: UserServiceDep,
    tenant_service: TenantServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List all users for a tenant."""
    # Verify tenant belongs to project
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    return await user_service.get_all_by_tenant(tenant_id, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_service: UserServiceDep,
    tenant_service: TenantServiceDep,
):
    """Get a user by ID."""
    # Verify tenant belongs to project
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    user = await user_service.get_by_id(user_id)
    if not user or user.tenant_id != tenant_id:
        raise NotFoundError("User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UserUpdate,
    user_service: UserServiceDep,
    tenant_service: TenantServiceDep,
):
    """Update a user."""
    # Verify tenant belongs to project
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    user = await user_service.get_by_id(user_id)
    if not user or user.tenant_id != tenant_id:
        raise NotFoundError("User not found")

    return await user_service.update(user_id, data)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_service: UserServiceDep,
    tenant_service: TenantServiceDep,
):
    """Delete a user."""
    # Verify tenant belongs to project
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    user = await user_service.get_by_id(user_id)
    if not user or user.tenant_id != tenant_id:
        raise NotFoundError("User not found")

    await user_service.delete(user_id)
