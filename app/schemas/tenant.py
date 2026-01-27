import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    slug: str
    schema_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
