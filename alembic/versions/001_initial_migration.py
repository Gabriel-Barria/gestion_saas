"""Initial migration - create projects, tenants, users tables

Revision ID: 001
Revises:
Create Date: 2024-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenant_strategy enum
    tenant_strategy_enum = postgresql.ENUM(
        "schema", "discriminator", name="tenantstrategy", create_type=False
    )
    tenant_strategy_enum.create(op.get_bind(), checkfirst=True)

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column(
            "tenant_strategy",
            sa.Enum("schema", "discriminator", name="tenantstrategy"),
            nullable=False,
            server_default="schema",
        ),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("jwt_secret", sa.String(255), nullable=False),
        sa.Column("jwt_algorithm", sa.String(50), nullable=False, server_default="HS256"),
        sa.Column("jwt_expiration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, index=True),
        sa.Column("schema_name", sa.String(255), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("roles", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create unique constraint for email within tenant
    op.create_unique_constraint(
        "uq_users_tenant_email", "users", ["tenant_id", "email"]
    )

    # Create unique constraint for slug within project
    op.create_unique_constraint(
        "uq_tenants_project_slug", "tenants", ["project_id", "slug"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_constraint("uq_tenants_project_slug", "tenants", type_="unique")
    op.drop_table("users")
    op.drop_table("tenants")
    op.drop_table("projects")

    # Drop enum
    tenant_strategy_enum = postgresql.ENUM(
        "schema", "discriminator", name="tenantstrategy"
    )
    tenant_strategy_enum.drop(op.get_bind(), checkfirst=True)
