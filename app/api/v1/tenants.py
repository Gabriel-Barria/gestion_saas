import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import TenantServiceDep, MembershipServiceDep, ApiKeyDep
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.membership import (
    MembershipResponse,
    MembershipUpdate,
    MembershipWithUser,
    InvitationCreate,
    InvitationResponse,
)
from app.schemas.user import UserBrief
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


# === Member Management ===

@router.get("/{tenant_id}/members", response_model=list[MembershipWithUser])
async def list_tenant_members(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    List all members of a tenant.

    Returns memberships with user details.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    memberships = await membership_service.get_tenant_members(tenant_id, skip, limit)

    return [
        MembershipWithUser(
            id=m.id,
            user_id=m.user_id,
            tenant_id=m.tenant_id,
            roles=m.roles,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
            user=UserBrief(
                id=m.user.id,
                email=m.user.email,
                full_name=m.user.full_name,
                is_active=m.user.is_active,
            ),
        )
        for m in memberships
    ]


@router.put("/{tenant_id}/members/{user_id}", response_model=MembershipResponse)
async def update_member(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MembershipUpdate,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
):
    """
    Update a member's roles or status.

    Use this to change a user's roles within the tenant or deactivate their access.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    membership = await membership_service.get_by_user_and_tenant(user_id, tenant_id)
    if not membership:
        raise NotFoundError("Member not found")

    return await membership_service.update(membership.id, data)


@router.delete("/{tenant_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
):
    """
    Remove a member from the tenant.

    This deletes the membership, not the user account.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    membership = await membership_service.get_by_user_and_tenant(user_id, tenant_id)
    if not membership:
        raise NotFoundError("Member not found")

    await membership_service.delete(membership.id)


# === Invitation Management ===

@router.get("/{tenant_id}/invitations", response_model=list[InvitationResponse])
async def list_tenant_invitations(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    List pending invitations for a tenant.

    Returns all invitations that haven't been used yet.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    return await membership_service.get_tenant_invitations(tenant_id, skip, limit)


@router.post("/{tenant_id}/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    data: InvitationCreate,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
):
    """
    Create an invitation to join the tenant.

    The invitation includes a token that can be shared with the invited user.
    The user can accept the invitation at `/auth/invitations/accept`.

    If the user doesn't have an account, they'll create one when accepting.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    return await membership_service.create_invitation(tenant_id, data)


@router.delete("/{tenant_id}/invitations/{invitation_id}", status_code=204)
async def delete_invitation(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    invitation_id: uuid.UUID,
    tenant_service: TenantServiceDep,
    membership_service: MembershipServiceDep,
):
    """
    Delete a pending invitation.

    This cancels the invitation so it can no longer be accepted.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    if not tenant or tenant.project_id != project_id:
        raise NotFoundError("Tenant not found")

    invitation = await membership_service.get_invitation_by_id(invitation_id)
    if not invitation or invitation.tenant_id != tenant_id:
        raise NotFoundError("Invitation not found")

    await membership_service.delete_invitation(invitation_id)
