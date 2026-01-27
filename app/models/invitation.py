import uuid
import secrets
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


def generate_token() -> str:
    """Generate a secure random token for invitations."""
    return secrets.token_urlsafe(32)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Invitation target
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Foreign Key
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Roles to assign when accepted
    roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Token for accepting the invitation
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, default=generate_token
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Usage tracking
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="invitations")

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the invitation has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the invitation is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def __repr__(self) -> str:
        return f"<Invitation {self.email} -> tenant={self.tenant_id}>"
