import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


TenantStrategyType = Literal["schema", "discriminator"]


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tenant_strategy: TenantStrategyType = "schema"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    tenant_strategy: TenantStrategyType | None = None
    is_active: bool | None = None
    jwt_algorithm: str | None = None
    jwt_expiration_minutes: int | None = Field(None, gt=0)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    tenant_strategy: str
    client_id: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectWithCredentials(ProjectResponse):
    """Response when creating a project - includes sensitive credentials (shown only once)."""
    api_key: str
    client_secret: str
    jwt_secret: str
