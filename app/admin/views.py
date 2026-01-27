from typing import Any
import uuid
from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import (
    generate_api_key,
    generate_client_id,
    generate_client_secret,
    generate_jwt_secret,
    hash_password,
)
from slugify import slugify as python_slugify
from app.database import async_session_maker


# ============================================================================
# HTML Templates
# ============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{title} - Gestion SaaS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar {{
            min-height: 100vh;
            background: #212529;
        }}
        .sidebar a {{
            color: #adb5bd;
            text-decoration: none;
            padding: 10px 20px;
            display: block;
        }}
        .sidebar a:hover, .sidebar a.active {{
            color: white;
            background: #343a40;
        }}
        .credential-box {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px 15px;
            font-family: monospace;
            word-break: break-all;
            position: relative;
        }}
        .copy-btn {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            color: #6c757d;
        }}
        .copy-btn:hover {{
            color: #212529;
        }}
        .breadcrumb-item a {{
            text-decoration: none;
        }}
        .card-stats {{
            border-left: 4px solid;
        }}
        .card-stats.primary {{ border-color: #0d6efd; }}
        .card-stats.success {{ border-color: #198754; }}
        .card-stats.info {{ border-color: #0dcaf0; }}
    </style>
</head>
<body>
    <div class="d-flex">
        <!-- Sidebar -->
        <div class="sidebar" style="width: 250px;">
            <div class="p-3 text-white">
                <h5><i class="fas fa-cogs"></i> Gestion SaaS</h5>
            </div>
            <nav>
                <a href="/admin/projects/" class="{nav_projects}">
                    <i class="fas fa-folder me-2"></i> Proyectos
                </a>
                <hr class="bg-secondary my-2">
                <a href="/admin" class="text-secondary small">
                    <i class="fas fa-arrow-left me-2"></i> Panel SQLAdmin
                </a>
                <a href="/docs" target="_blank" class="text-secondary small">
                    <i class="fas fa-book me-2"></i> API Docs
                </a>
            </nav>
        </div>

        <!-- Main Content -->
        <div class="flex-grow-1 bg-light">
            <div class="p-4">
                {content}
            </div>
        </div>
    </div>

    <script>
        function copyToClipboard(elementId) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const btn = event.target;
                const originalClass = btn.className;
                btn.className = 'fas fa-check copy-btn text-success';
                setTimeout(() => {{ btn.className = originalClass; }}, 1500);
            }});
        }}
    </script>
</body>
</html>
"""


# ============================================================================
# Projects View
# ============================================================================

class ProjectsView(BaseView):
    name = "Proyectos"
    icon = "fa-solid fa-folder"
    identity = "projects"

    @expose("/", methods=["GET"])
    async def list_projects(self, request: Request) -> HTMLResponse:
        """List all projects."""
        async with async_session_maker() as session:
            # Get projects with tenant count
            result = await session.execute(
                select(Project).order_by(Project.created_at.desc())
            )
            projects = result.scalars().all()

            # Get tenant counts
            tenant_counts = {}
            for project in projects:
                count_result = await session.execute(
                    select(func.count(Tenant.id)).where(Tenant.project_id == project.id)
                )
                tenant_counts[project.id] = count_result.scalar() or 0

        projects_html = ""
        for project in projects:
            status_badge = '<span class="badge bg-success">Activo</span>' if project.is_active else '<span class="badge bg-secondary">Inactivo</span>'
            projects_html += f"""
            <tr>
                <td>
                    <a href="/admin/projects/{project.id}" class="fw-bold text-decoration-none">
                        {project.name}
                    </a>
                    <br><small class="text-muted">{project.slug}</small>
                </td>
                <td><code>{project.client_id[:20]}...</code></td>
                <td><span class="badge bg-info">{project.tenant_strategy}</span></td>
                <td>{tenant_counts.get(project.id, 0)}</td>
                <td>{status_badge}</td>
                <td>{project.created_at.strftime('%Y-%m-%d %H:%M')}</td>
                <td>
                    <a href="/admin/projects/{project.id}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i>
                    </a>
                </td>
            </tr>
            """

        if not projects:
            projects_html = """
            <tr>
                <td colspan="7" class="text-center py-5">
                    <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No hay proyectos creados</p>
                    <a href="/admin/projects/create" class="btn btn-primary">
                        <i class="fas fa-plus"></i> Crear Primer Proyecto
                    </a>
                </td>
            </tr>
            """

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item active">Proyectos</li>
            </ol>
        </nav>

        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2><i class="fas fa-folder me-2"></i> Proyectos</h2>
            <a href="/admin/projects/create" class="btn btn-primary">
                <i class="fas fa-plus"></i> Nuevo Proyecto
            </a>
        </div>

        <div class="card">
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Client ID</th>
                            <th>Estrategia</th>
                            <th>Tenants</th>
                            <th>Estado</th>
                            <th>Creado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {projects_html}
                    </tbody>
                </table>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title="Proyectos",
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)

    @expose("/create", methods=["GET", "POST"])
    async def create_project(self, request: Request) -> HTMLResponse:
        """Create a new project."""
        error = None

        if request.method == "POST":
            form = await request.form()
            name = form.get("name", "").strip()
            tenant_strategy = form.get("tenant_strategy", "schema")
            jwt_algorithm = form.get("jwt_algorithm", "HS256")
            jwt_expiration = int(form.get("jwt_expiration_minutes", 30))

            if not name:
                error = "El nombre es requerido"
            else:
                # Generate credentials
                api_key = generate_api_key()
                client_id = generate_client_id()
                client_secret = generate_client_secret()
                jwt_secret = generate_jwt_secret()
                slug = python_slugify(name)

                async with async_session_maker() as session:
                    # Check if slug exists
                    existing = await session.execute(
                        select(Project).where(Project.slug == slug)
                    )
                    if existing.scalar_one_or_none():
                        slug = f"{slug}-{uuid.uuid4().hex[:8]}"

                    project = Project(
                        name=name,
                        slug=slug,
                        tenant_strategy=tenant_strategy,
                        api_key_hash=hash_password(api_key),
                        client_id=client_id,
                        client_secret_hash=hash_password(client_secret),
                        jwt_secret=jwt_secret,
                        jwt_algorithm=jwt_algorithm,
                        jwt_expiration_minutes=jwt_expiration,
                    )
                    session.add(project)
                    await session.commit()
                    await session.refresh(project)

                    # Store credentials in session
                    request.session["project_credentials"] = {
                        "project_id": str(project.id),
                        "api_key": api_key,
                        "client_secret": client_secret,
                    }

                    return RedirectResponse(
                        url=f"/admin/projects/{project.id}?created=1",
                        status_code=302
                    )

        error_html = f'<div class="alert alert-danger">{error}</div>' if error else ""

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/admin/projects/">Proyectos</a></li>
                <li class="breadcrumb-item active">Nuevo Proyecto</li>
            </ol>
        </nav>

        <div class="card" style="max-width: 600px;">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-plus me-2"></i> Crear Nuevo Proyecto</h5>
            </div>
            <div class="card-body">
                {error_html}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Nombre del Proyecto *</label>
                        <input type="text" name="name" class="form-control" required
                               placeholder="Mi Proyecto SaaS">
                        <div class="form-text">El slug se generará automáticamente</div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Estrategia de Tenants</label>
                        <select name="tenant_strategy" class="form-select">
                            <option value="schema">Schema (un schema PostgreSQL por tenant)</option>
                            <option value="discriminator">Discriminator (columna tenant_id)</option>
                        </select>
                    </div>

                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Algoritmo JWT</label>
                            <select name="jwt_algorithm" class="form-select">
                                <option value="HS256">HS256</option>
                                <option value="HS384">HS384</option>
                                <option value="HS512">HS512</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Expiración JWT (minutos)</label>
                            <input type="number" name="jwt_expiration_minutes"
                                   class="form-control" value="30" min="1">
                        </div>
                    </div>

                    <hr>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Crear Proyecto
                        </button>
                        <a href="/admin/projects/" class="btn btn-outline-secondary">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title="Nuevo Proyecto",
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)

    @expose("/{project_id}", methods=["GET"])
    async def view_project(self, request: Request) -> HTMLResponse:
        """View a project with its tenants."""
        project_id = request.path_params["project_id"]

        # Validate UUID format
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            return RedirectResponse(url="/admin/projects/", status_code=302)

        show_credentials = request.query_params.get("created") == "1"

        async with async_session_maker() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_uuid)
            )
            project = result.scalar_one_or_none()

            if not project:
                return RedirectResponse(url="/admin/projects/", status_code=302)

            # Get tenants
            tenants_result = await session.execute(
                select(Tenant)
                .where(Tenant.project_id == project.id)
                .order_by(Tenant.created_at.desc())
            )
            tenants = tenants_result.scalars().all()

            # Get user counts per tenant
            user_counts = {}
            for tenant in tenants:
                count_result = await session.execute(
                    select(func.count(User.id)).where(User.tenant_id == tenant.id)
                )
                user_counts[tenant.id] = count_result.scalar() or 0

        # Check for new credentials in session
        credentials_html = ""
        if show_credentials and "project_credentials" in request.session:
            creds = request.session.pop("project_credentials", {})
            if creds.get("project_id") == project_id:
                credentials_html = f"""
                <div class="alert alert-warning mb-4">
                    <h5><i class="fas fa-exclamation-triangle"></i> Credenciales Generadas</h5>
                    <p class="mb-2"><strong>Guarda estas credenciales ahora. No se mostrarán de nuevo.</strong></p>

                    <div class="row g-3 mt-2">
                        <div class="col-12">
                            <label class="form-label fw-bold">API Key</label>
                            <div class="credential-box">
                                <span id="api-key">{creds['api_key']}</span>
                                <i class="fas fa-copy copy-btn" onclick="copyToClipboard('api-key')"></i>
                            </div>
                        </div>
                        <div class="col-12">
                            <label class="form-label fw-bold">Client Secret</label>
                            <div class="credential-box">
                                <span id="client-secret">{creds['client_secret']}</span>
                                <i class="fas fa-copy copy-btn" onclick="copyToClipboard('client-secret')"></i>
                            </div>
                        </div>
                    </div>
                </div>
                """

        # Tenants table
        tenants_html = ""
        for tenant in tenants:
            status_badge = '<span class="badge bg-success">Activo</span>' if tenant.is_active else '<span class="badge bg-secondary">Inactivo</span>'
            tenants_html += f"""
            <tr>
                <td>
                    <a href="/admin/projects/{project_id}/tenants/{tenant.id}" class="fw-bold text-decoration-none">
                        {tenant.name}
                    </a>
                    <br><small class="text-muted">{tenant.slug}</small>
                </td>
                <td><code>{tenant.schema_name or 'N/A'}</code></td>
                <td>{user_counts.get(tenant.id, 0)}</td>
                <td>{status_badge}</td>
                <td>
                    <a href="/admin/projects/{project_id}/tenants/{tenant.id}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i> Ver
                    </a>
                </td>
            </tr>
            """

        if not tenants:
            tenants_html = """
            <tr>
                <td colspan="5" class="text-center py-4">
                    <p class="text-muted mb-2">No hay tenants en este proyecto</p>
                </td>
            </tr>
            """

        status_badge = '<span class="badge bg-success">Activo</span>' if project.is_active else '<span class="badge bg-secondary">Inactivo</span>'

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/admin/projects/">Proyectos</a></li>
                <li class="breadcrumb-item active">{project.name}</li>
            </ol>
        </nav>

        {credentials_html}

        <div class="d-flex justify-content-between align-items-start mb-4">
            <div>
                <h2><i class="fas fa-folder-open me-2"></i> {project.name}</h2>
                <p class="text-muted mb-0">Slug: <code>{project.slug}</code></p>
            </div>
            <div>
                {status_badge}
            </div>
        </div>

        <!-- Project Info Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card card-stats primary">
                    <div class="card-body">
                        <h6 class="text-muted">Client ID</h6>
                        <div class="credential-box">
                            <span id="client-id">{project.client_id}</span>
                            <i class="fas fa-copy copy-btn" onclick="copyToClipboard('client-id')"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card card-stats success">
                    <div class="card-body">
                        <h6 class="text-muted">Estrategia</h6>
                        <span class="badge bg-info fs-6">{project.tenant_strategy}</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card card-stats info">
                    <div class="card-body">
                        <h6 class="text-muted">JWT</h6>
                        <span>{project.jwt_algorithm} / {project.jwt_expiration_minutes} min</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Usage Example -->
        <div class="card mb-4">
            <div class="card-header">
                <h6 class="mb-0"><i class="fas fa-code me-2"></i> Ejemplo de Uso</h6>
            </div>
            <div class="card-body">
                <pre class="bg-dark text-light p-3 rounded mb-0"><code># Obtener token (reemplaza API_KEY con tu API Key)
curl -X POST http://localhost:8000/api/v1/auth/token \\
  -H "X-API-Key: TU_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "usuario@ejemplo.com", "password": "pass", "tenant_slug": "mi-tenant"}}'

# O usar OAuth2
curl -X POST http://localhost:8000/api/v1/auth/oauth/token \\
  -H "Content-Type: application/json" \\
  -d '{{
    "grant_type": "password",
    "client_id": "{project.client_id}",
    "client_secret": "TU_CLIENT_SECRET",
    "username": "usuario@ejemplo.com",
    "password": "pass",
    "tenant": "mi-tenant"
  }}'</code></pre>
            </div>
        </div>

        <!-- Tenants Section -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0"><i class="fas fa-building me-2"></i> Tenants</h5>
                <a href="/admin/projects/{project_id}/tenants/create" class="btn btn-sm btn-success">
                    <i class="fas fa-plus"></i> Nuevo Tenant
                </a>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Schema</th>
                            <th>Usuarios</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tenants_html}
                    </tbody>
                </table>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title=project.name,
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)

    @expose("/{project_id}/tenants/create", methods=["GET", "POST"])
    async def create_tenant(self, request: Request) -> HTMLResponse:
        """Create a tenant for a project."""
        project_id = request.path_params["project_id"]

        # Validate UUID format
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            return RedirectResponse(url="/admin/projects/", status_code=302)

        async with async_session_maker() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_uuid)
            )
            project = result.scalar_one_or_none()

            if not project:
                return RedirectResponse(url="/admin/projects/", status_code=302)

        error = None

        if request.method == "POST":
            form = await request.form()
            name = form.get("name", "").strip()

            if not name:
                error = "El nombre es requerido"
            else:
                slug = python_slugify(name)

                async with async_session_maker() as session:
                    # Check if slug exists in this project
                    existing = await session.execute(
                        select(Tenant).where(
                            Tenant.project_id == uuid.UUID(project_id),
                            Tenant.slug == slug
                        )
                    )
                    if existing.scalar_one_or_none():
                        slug = f"{slug}-{uuid.uuid4().hex[:8]}"

                    # Create schema if needed
                    schema_name = None
                    if project.tenant_strategy == "schema":
                        schema_name = f"tenant_{project.slug}_{slug}".replace("-", "_")
                        # Create schema
                        from app.database import create_schema
                        await create_schema(schema_name)

                    tenant = Tenant(
                        project_id=uuid.UUID(project_id),
                        name=name,
                        slug=slug,
                        schema_name=schema_name,
                    )
                    session.add(tenant)
                    await session.commit()

                    return RedirectResponse(
                        url=f"/admin/projects/{project_id}",
                        status_code=302
                    )

        error_html = f'<div class="alert alert-danger">{error}</div>' if error else ""

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/admin/projects/">Proyectos</a></li>
                <li class="breadcrumb-item"><a href="/admin/projects/{project_id}">{project.name}</a></li>
                <li class="breadcrumb-item active">Nuevo Tenant</li>
            </ol>
        </nav>

        <div class="card" style="max-width: 500px;">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-building me-2"></i> Crear Tenant en {project.name}</h5>
            </div>
            <div class="card-body">
                {error_html}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Nombre del Tenant *</label>
                        <input type="text" name="name" class="form-control" required
                               placeholder="Empresa ABC">
                        <div class="form-text">El slug se generará automáticamente</div>
                    </div>

                    <div class="alert alert-info">
                        <small>
                            <i class="fas fa-info-circle"></i>
                            Estrategia: <strong>{project.tenant_strategy}</strong>
                            {"- Se creará un schema PostgreSQL para este tenant" if project.tenant_strategy == "schema" else "- Se usará columna discriminadora"}
                        </small>
                    </div>

                    <hr>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-success">
                            <i class="fas fa-save"></i> Crear Tenant
                        </button>
                        <a href="/admin/projects/{project_id}" class="btn btn-outline-secondary">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title=f"Nuevo Tenant - {project.name}",
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)

    @expose("/{project_id}/tenants/{tenant_id}", methods=["GET"])
    async def view_tenant(self, request: Request) -> HTMLResponse:
        """View a tenant with its users."""
        project_id = request.path_params["project_id"]
        tenant_id = request.path_params["tenant_id"]

        # Validate UUID format
        try:
            project_uuid = uuid.UUID(project_id)
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            return RedirectResponse(url="/admin/projects/", status_code=302)

        async with async_session_maker() as session:
            # Get project
            project_result = await session.execute(
                select(Project).where(Project.id == project_uuid)
            )
            project = project_result.scalar_one_or_none()

            if not project:
                return RedirectResponse(url="/admin/projects/", status_code=302)

            # Get tenant
            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_uuid)
            )
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=302)

            # Get users
            users_result = await session.execute(
                select(User)
                .where(User.tenant_id == tenant_uuid)
                .order_by(User.created_at.desc())
            )
            users = users_result.scalars().all()

        # Check for new user credentials
        user_credentials_html = ""
        if "new_user_password" in request.session:
            user_info = request.session.pop("new_user_password", {})
            if user_info.get("tenant_id") == tenant_id:
                user_credentials_html = f"""
                <div class="alert alert-warning mb-4">
                    <h5><i class="fas fa-key"></i> Usuario Creado</h5>
                    <p>Email: <strong>{user_info['email']}</strong></p>
                    <p>Password temporal: <code>{user_info['password']}</code></p>
                    <small class="text-muted">El usuario debe cambiar esta contraseña al iniciar sesión.</small>
                </div>
                """

        # Users table
        users_html = ""
        for user in users:
            status_badge = '<span class="badge bg-success">Activo</span>' if user.is_active else '<span class="badge bg-secondary">Inactivo</span>'
            roles = ", ".join(user.roles) if user.roles else "Sin roles"
            users_html += f"""
            <tr>
                <td>
                    <strong>{user.email}</strong>
                    <br><small class="text-muted">{user.full_name or 'Sin nombre'}</small>
                </td>
                <td><span class="badge bg-secondary">{roles}</span></td>
                <td>{status_badge}</td>
                <td>{user.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            </tr>
            """

        if not users:
            users_html = """
            <tr>
                <td colspan="4" class="text-center py-4">
                    <p class="text-muted mb-0">No hay usuarios en este tenant</p>
                </td>
            </tr>
            """

        status_badge = '<span class="badge bg-success">Activo</span>' if tenant.is_active else '<span class="badge bg-secondary">Inactivo</span>'

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/admin/projects/">Proyectos</a></li>
                <li class="breadcrumb-item"><a href="/admin/projects/{project_id}">{project.name}</a></li>
                <li class="breadcrumb-item active">{tenant.name}</li>
            </ol>
        </nav>

        {user_credentials_html}

        <div class="d-flex justify-content-between align-items-start mb-4">
            <div>
                <h2><i class="fas fa-building me-2"></i> {tenant.name}</h2>
                <p class="text-muted mb-0">Slug: <code>{tenant.slug}</code></p>
            </div>
            <div>
                {status_badge}
            </div>
        </div>

        <!-- Tenant Info -->
        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h6 class="text-muted">Schema</h6>
                        <code>{tenant.schema_name or 'N/A (discriminator)'}</code>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h6 class="text-muted">Proyecto</h6>
                        <a href="/admin/projects/{project_id}">{project.name}</a>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h6 class="text-muted">Creado</h6>
                        {tenant.created_at.strftime('%Y-%m-%d %H:%M')}
                    </div>
                </div>
            </div>
        </div>

        <!-- Users Section -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0"><i class="fas fa-users me-2"></i> Usuarios</h5>
                <a href="/admin/projects/{project_id}/tenants/{tenant_id}/users/create" class="btn btn-sm btn-primary">
                    <i class="fas fa-plus"></i> Nuevo Usuario
                </a>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Email / Nombre</th>
                            <th>Roles</th>
                            <th>Estado</th>
                            <th>Creado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users_html}
                    </tbody>
                </table>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title=f"{tenant.name} - {project.name}",
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)

    @expose("/{project_id}/tenants/{tenant_id}/users/create", methods=["GET", "POST"])
    async def create_user(self, request: Request) -> HTMLResponse:
        """Create a user for a tenant."""
        project_id = request.path_params["project_id"]
        tenant_id = request.path_params["tenant_id"]

        # Validate UUID format
        try:
            project_uuid = uuid.UUID(project_id)
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            return RedirectResponse(url="/admin/projects/", status_code=302)

        async with async_session_maker() as session:
            # Get project
            project_result = await session.execute(
                select(Project).where(Project.id == project_uuid)
            )
            project = project_result.scalar_one_or_none()

            if not project:
                return RedirectResponse(url="/admin/projects/", status_code=302)

            # Get tenant
            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_uuid)
            )
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                return RedirectResponse(url=f"/admin/projects/{project_id}", status_code=302)

        error = None

        if request.method == "POST":
            form = await request.form()
            email = form.get("email", "").strip()
            full_name = form.get("full_name", "").strip()
            roles_str = form.get("roles", "").strip()

            if not email:
                error = "El email es requerido"
            else:
                roles = [r.strip() for r in roles_str.split(",") if r.strip()] if roles_str else []
                default_password = "changeme123"

                async with async_session_maker() as session:
                    # Check if email exists in this tenant
                    existing = await session.execute(
                        select(User).where(
                            User.tenant_id == uuid.UUID(tenant_id),
                            User.email == email
                        )
                    )
                    if existing.scalar_one_or_none():
                        error = "Ya existe un usuario con ese email en este tenant"
                    else:
                        user = User(
                            tenant_id=uuid.UUID(tenant_id),
                            email=email,
                            full_name=full_name or None,
                            password_hash=hash_password(default_password),
                            roles=roles,
                        )
                        session.add(user)
                        await session.commit()

                        # Store password to show
                        request.session["new_user_password"] = {
                            "tenant_id": tenant_id,
                            "email": email,
                            "password": default_password,
                        }

                        return RedirectResponse(
                            url=f"/admin/projects/{project_id}/tenants/{tenant_id}",
                            status_code=302
                        )

        error_html = f'<div class="alert alert-danger">{error}</div>' if error else ""

        content = f"""
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/admin/projects/">Proyectos</a></li>
                <li class="breadcrumb-item"><a href="/admin/projects/{project_id}">{project.name}</a></li>
                <li class="breadcrumb-item"><a href="/admin/projects/{project_id}/tenants/{tenant_id}">{tenant.name}</a></li>
                <li class="breadcrumb-item active">Nuevo Usuario</li>
            </ol>
        </nav>

        <div class="card" style="max-width: 500px;">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-user-plus me-2"></i> Crear Usuario en {tenant.name}</h5>
            </div>
            <div class="card-body">
                {error_html}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Email *</label>
                        <input type="email" name="email" class="form-control" required
                               placeholder="usuario@ejemplo.com">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Nombre Completo</label>
                        <input type="text" name="full_name" class="form-control"
                               placeholder="Juan Pérez">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Roles</label>
                        <input type="text" name="roles" class="form-control"
                               placeholder="admin, user">
                        <div class="form-text">Separados por coma</div>
                    </div>

                    <div class="alert alert-info">
                        <small>
                            <i class="fas fa-info-circle"></i>
                            Se asignará la contraseña temporal <code>changeme123</code>
                        </small>
                    </div>

                    <hr>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Crear Usuario
                        </button>
                        <a href="/admin/projects/{project_id}/tenants/{tenant_id}" class="btn btn-outline-secondary">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
        """

        html = BASE_TEMPLATE.format(
            title=f"Nuevo Usuario - {tenant.name}",
            nav_projects="active",
            content=content
        )
        return HTMLResponse(content=html)
