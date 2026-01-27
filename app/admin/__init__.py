from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.database import engine
from app.config import settings
from app.admin.views import ProjectAdmin, TenantAdmin, UserAdmin


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Simple authentication with env credentials
        if username == settings.ADMIN_EMAIL and password == settings.ADMIN_PASSWORD:
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)


def setup_admin(app) -> Admin:
    """Configure and return the admin panel."""
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Gestion SaaS - Admin",
        base_url="/admin",
    )

    # Register model views
    admin.add_view(ProjectAdmin)
    admin.add_view(TenantAdmin)
    admin.add_view(UserAdmin)

    return admin
