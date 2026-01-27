from sqladmin import ModelView

from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User


class ProjectAdmin(ModelView, model=Project):
    name = "Project"
    name_plural = "Projects"
    icon = "fa-solid fa-folder"

    column_list = [
        Project.id,
        Project.name,
        Project.slug,
        Project.tenant_strategy,
        Project.client_id,
        Project.is_active,
        Project.created_at,
    ]

    column_searchable_list = [Project.name, Project.slug, Project.client_id]
    column_sortable_list = [Project.name, Project.created_at, Project.is_active]
    column_default_sort = ("created_at", True)

    # Only show these fields in forms (excludes sensitive data)
    form_columns = [
        Project.name,
        Project.slug,
        Project.tenant_strategy,
        Project.jwt_algorithm,
        Project.jwt_expiration_minutes,
        Project.is_active,
    ]

    column_details_list = [
        Project.id,
        Project.name,
        Project.slug,
        Project.tenant_strategy,
        Project.client_id,
        Project.jwt_algorithm,
        Project.jwt_expiration_minutes,
        Project.is_active,
        Project.created_at,
        Project.updated_at,
    ]

    can_create = False  # Projects should be created via API to generate credentials
    can_export = True


class TenantAdmin(ModelView, model=Tenant):
    name = "Tenant"
    name_plural = "Tenants"
    icon = "fa-solid fa-building"

    column_list = [
        Tenant.id,
        Tenant.name,
        Tenant.slug,
        Tenant.project,
        Tenant.schema_name,
        Tenant.is_active,
        Tenant.created_at,
    ]

    column_searchable_list = [Tenant.name, Tenant.slug, Tenant.schema_name]
    column_sortable_list = [Tenant.name, Tenant.created_at, Tenant.is_active]
    column_default_sort = ("created_at", True)

    form_columns = [
        Tenant.name,
        Tenant.slug,
        Tenant.project,
        Tenant.is_active,
    ]

    column_details_list = [
        Tenant.id,
        Tenant.name,
        Tenant.slug,
        Tenant.project,
        Tenant.schema_name,
        Tenant.is_active,
        Tenant.created_at,
        Tenant.updated_at,
    ]

    can_create = False  # Tenants should be created via API to handle schema creation
    can_export = True


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"

    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.tenant,
        User.roles,
        User.is_active,
        User.created_at,
    ]

    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.email, User.created_at, User.is_active]
    column_default_sort = ("created_at", True)

    form_columns = [
        User.email,
        User.full_name,
        User.tenant,
        User.roles,
        User.is_active,
    ]

    column_details_list = [
        User.id,
        User.email,
        User.full_name,
        User.tenant,
        User.roles,
        User.is_active,
        User.created_at,
        User.updated_at,
    ]

    can_create = False  # Users should be created via API to hash passwords
    can_export = True
