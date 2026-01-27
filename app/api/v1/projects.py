import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ProjectServiceDep
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithCredentials,
)
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectWithCredentials, status_code=201)
async def create_project(
    data: ProjectCreate,
    service: ProjectServiceDep,
):
    """
    Create a new project.

    Returns the project with credentials (API key, client_id, client_secret).
    These credentials are only shown once, so save them securely.
    """
    project, credentials = await service.create(data)

    return ProjectWithCredentials(
        id=project.id,
        name=project.name,
        slug=project.slug,
        tenant_strategy=project.tenant_strategy,
        client_id=project.client_id,
        jwt_algorithm=project.jwt_algorithm,
        jwt_expiration_minutes=project.jwt_expiration_minutes,
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
        api_key=credentials["api_key"],
        client_secret=credentials["client_secret"],
        jwt_secret=credentials["jwt_secret"],
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    service: ProjectServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List all projects with pagination."""
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
):
    """Get a project by ID."""
    project = await service.get_by_id(project_id)
    if not project:
        raise NotFoundError("Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    service: ProjectServiceDep,
):
    """Update a project."""
    return await service.update(project_id, data)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
):
    """Delete a project and all its tenants."""
    await service.delete(project_id)


@router.post("/{project_id}/regenerate-api-key")
async def regenerate_api_key(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
):
    """
    Regenerate the API key for a project.

    Returns the new API key (shown only once).
    """
    new_key = await service.regenerate_api_key(project_id)
    return {"api_key": new_key}


@router.post("/{project_id}/regenerate-client-secret")
async def regenerate_client_secret(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
):
    """
    Regenerate the client secret for a project.

    Returns the new client secret (shown only once).
    """
    new_secret = await service.regenerate_client_secret(project_id)
    return {"client_secret": new_secret}
