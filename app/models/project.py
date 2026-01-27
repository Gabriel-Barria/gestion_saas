import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TenantStrategy(str, PyEnum):
    SCHEMA = "schema"
    DISCRIMINATOR = "discriminator"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Tenant strategy configuration (stored as string, validated in code)
    tenant_strategy: Mapped[str] = mapped_column(
        String(50), default=TenantStrategy.SCHEMA.value, nullable=False
    )

    # API Key authentication
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # OAuth2 credentials
    client_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # JWT configuration per project
    jwt_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    jwt_algorithm: Mapped[str] = mapped_column(String(50), default="HS256", nullable=False)
    jwt_expiration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    tenants: Mapped[list["Tenant"]] = relationship(
        "Tenant", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.slug})>"
