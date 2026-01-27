"""Custom admin routes for project and tenant management."""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.models.membership import Membership
from app.models.invitation import Invitation
from app.core.security import (
    generate_api_key,
    generate_client_id,
    generate_client_secret,
    generate_jwt_secret,
    hash_secret,
)
from slugify import slugify as python_slugify
from app.database import get_db, create_schema

router = APIRouter(prefix="/panel", tags=["Admin Panel"])


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
                <a href="/panel/" class="{nav_projects}">
                    <i class="fas fa-folder me-2"></i> Proyectos
                </a>
                <a href="/panel/users" class="{nav_users}">
                    <i class="fas fa-users me-2"></i> Usuarios
                </a>
                <hr class="bg-secondary my-2">
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
# Routes
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def list_projects(request: Request, db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    # Get tenant counts
    tenant_counts = {}
    for project in projects:
        count_result = await db.execute(
            select(func.count(Tenant.id)).where(Tenant.project_id == project.id)
        )
        tenant_counts[project.id] = count_result.scalar() or 0

    projects_html = ""
    for project in projects:
        status_badge = '<span class="badge bg-success">Activo</span>' if project.is_active else '<span class="badge bg-secondary">Inactivo</span>'
        projects_html += f"""
        <tr>
            <td>
                <a href="/panel/{project.id}" class="fw-bold text-decoration-none">
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
                <a href="/panel/{project.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye"></i>
                </a>
            </td>
        </tr>
        """

    if not projects:
        projects_html = """
        <tr>
            <td colspan="7" class="text-center py-5">
                <i class="fas fa-folder-open fa-3x text-muted mb-3 d-block"></i>
                <p class="text-muted">No hay proyectos creados</p>
                <a href="/panel/create" class="btn btn-primary">
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
        <a href="/panel/create" class="btn btn-primary">
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
        nav_users="",
        content=content
    )
    return HTMLResponse(content=html)


@router.get("/create", response_class=HTMLResponse)
async def create_project_form(request: Request):
    """Show create project form."""
    content = """
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/panel/">Proyectos</a></li>
            <li class="breadcrumb-item active">Nuevo Proyecto</li>
        </ol>
    </nav>

    <div class="card" style="max-width: 600px;">
        <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-plus me-2"></i> Crear Nuevo Proyecto</h5>
        </div>
        <div class="card-body">
            <form method="POST" action="/panel/create">
                <div class="mb-3">
                    <label class="form-label">Nombre del Proyecto *</label>
                    <input type="text" name="name" class="form-control" required
                           placeholder="Mi Proyecto SaaS">
                    <div class="form-text">El slug se generara automaticamente</div>
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
                        <label class="form-label">Expiracion JWT (minutos)</label>
                        <input type="number" name="jwt_expiration_minutes"
                               class="form-control" value="30" min="1">
                    </div>
                </div>

                <hr>
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Crear Proyecto
                    </button>
                    <a href="/panel/" class="btn btn-outline-secondary">Cancelar</a>
                </div>
            </form>
        </div>
    </div>
    """

    html = BASE_TEMPLATE.format(
        title="Nuevo Proyecto",
        nav_projects="active",
        nav_users="",
        content=content
    )
    return HTMLResponse(content=html)


@router.post("/create", response_class=HTMLResponse)
async def create_project(request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    form = await request.form()
    name = form.get("name", "").strip()
    tenant_strategy = form.get("tenant_strategy", "schema")
    jwt_algorithm = form.get("jwt_algorithm", "HS256")
    jwt_expiration = int(form.get("jwt_expiration_minutes", 30))

    # Generate credentials
    api_key = generate_api_key()
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    jwt_secret = generate_jwt_secret()
    slug = python_slugify(name)

    # Check if slug exists
    existing = await db.execute(
        select(Project).where(Project.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:8]}"

    project = Project(
        name=name,
        slug=slug,
        tenant_strategy=tenant_strategy,
        api_key_hash=hash_secret(api_key),
        client_id=client_id,
        client_secret_hash=hash_secret(client_secret),
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_expiration_minutes=jwt_expiration,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Store credentials in session
    request.session["project_credentials"] = {
        "project_id": str(project.id),
        "api_key": api_key,
        "client_secret": client_secret,
    }

    return RedirectResponse(
        url=f"/panel/{project.id}?created=1",
        status_code=302
    )


# ============================================================================
# User Management Routes (MUST be before /{project_id} to avoid route conflict)
# ============================================================================

@router.get("/users", response_class=HTMLResponse)
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    """List all users."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    # Get membership counts
    membership_counts = {}
    for user in users:
        count_result = await db.execute(
            select(func.count(Membership.id)).where(Membership.user_id == user.id)
        )
        membership_counts[user.id] = count_result.scalar() or 0

    users_html = ""
    for user in users:
        status_badge = '<span class="badge bg-success">Activo</span>' if user.is_active else '<span class="badge bg-secondary">Inactivo</span>'
        verified_badge = '<i class="fas fa-check-circle text-success"></i>' if user.email_verified else '<i class="fas fa-times-circle text-muted"></i>'
        users_html += f"""
        <tr>
            <td>
                <strong>{user.full_name}</strong>
                <br><small class="text-muted">{user.email}</small>
            </td>
            <td>{verified_badge}</td>
            <td><span class="badge bg-info">{membership_counts.get(user.id, 0)}</span></td>
            <td>{status_badge}</td>
            <td>{user.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <a href="/panel/users/{user.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye"></i>
                </a>
            </td>
        </tr>
        """

    if not users:
        users_html = """
        <tr>
            <td colspan="6" class="text-center py-5">
                <i class="fas fa-users fa-3x text-muted mb-3 d-block"></i>
                <p class="text-muted">No hay usuarios registrados</p>
            </td>
        </tr>
        """

    content = f"""
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item active">Usuarios</li>
        </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-users me-2"></i> Usuarios</h2>
    </div>

    <div class="card">
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>Verificado</th>
                        <th>Membresías</th>
                        <th>Estado</th>
                        <th>Registro</th>
                        <th>Acciones</th>
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
        title="Usuarios",
        nav_projects="",
        nav_users="active",
        content=content
    )
    return HTMLResponse(content=html)


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def view_user(request: Request, user_id: str, db: AsyncSession = Depends(get_db)):
    """View user details with memberships."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/panel/users", status_code=302)

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        return RedirectResponse(url="/panel/users", status_code=302)

    # Get memberships with tenant and project info
    memberships_result = await db.execute(
        select(Membership)
        .options(selectinload(Membership.tenant).selectinload(Tenant.project))
        .where(Membership.user_id == user_uuid)
        .order_by(Membership.created_at.desc())
    )
    memberships = memberships_result.scalars().all()

    memberships_html = ""
    for m in memberships:
        status_badge = '<span class="badge bg-success">Activo</span>' if m.is_active else '<span class="badge bg-secondary">Inactivo</span>'
        roles_badges = " ".join([f'<span class="badge bg-primary">{r}</span>' for r in m.roles]) or '<span class="text-muted">Sin roles</span>'
        memberships_html += f"""
        <tr>
            <td>
                <strong>{m.tenant.project.name}</strong>
                <br><small class="text-muted">{m.tenant.project.slug}</small>
            </td>
            <td>
                <strong>{m.tenant.name}</strong>
                <br><small class="text-muted">{m.tenant.slug}</small>
            </td>
            <td>{roles_badges}</td>
            <td>{status_badge}</td>
            <td>{m.created_at.strftime('%Y-%m-%d %H:%M')}</td>
        </tr>
        """

    if not memberships:
        memberships_html = """
        <tr>
            <td colspan="5" class="text-center py-4">
                <p class="text-muted mb-0">Este usuario no tiene membresías</p>
            </td>
        </tr>
        """

    status_badge = '<span class="badge bg-success">Activo</span>' if user.is_active else '<span class="badge bg-secondary">Inactivo</span>'
    verified_badge = '<span class="badge bg-success">Verificado</span>' if user.email_verified else '<span class="badge bg-warning">No verificado</span>'

    content = f"""
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/panel/users">Usuarios</a></li>
            <li class="breadcrumb-item active">{user.full_name}</li>
        </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
            <h2><i class="fas fa-user me-2"></i> {user.full_name}</h2>
            <p class="text-muted mb-0">{user.email}</p>
        </div>
        <div>
            {status_badge} {verified_badge}
        </div>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card card-stats primary">
                <div class="card-body">
                    <h6 class="text-muted">ID</h6>
                    <code class="small">{user.id}</code>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stats success">
                <div class="card-body">
                    <h6 class="text-muted">Registrado</h6>
                    <span>{user.created_at.strftime('%Y-%m-%d %H:%M')}</span>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stats info">
                <div class="card-body">
                    <h6 class="text-muted">Membresías</h6>
                    <span class="fs-4">{len(memberships)}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-id-badge me-2"></i> Membresías</h5>
        </div>
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Proyecto</th>
                        <th>Tenant</th>
                        <th>Roles</th>
                        <th>Estado</th>
                        <th>Desde</th>
                    </tr>
                </thead>
                <tbody>
                    {memberships_html}
                </tbody>
            </table>
        </div>
    </div>
    """

    html = BASE_TEMPLATE.format(
        title=user.full_name,
        nav_projects="",
        nav_users="active",
        content=content
    )
    return HTMLResponse(content=html)


# ============================================================================
# Project Routes
# ============================================================================

@router.get("/{project_id}", response_class=HTMLResponse)
async def view_project(request: Request, project_id: str, db: AsyncSession = Depends(get_db)):
    """View a project with its tenants."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        return RedirectResponse(url="/panel/", status_code=302)

    show_credentials = request.query_params.get("created") == "1"

    result = await db.execute(
        select(Project).where(Project.id == project_uuid)
    )
    project = result.scalar_one_or_none()

    if not project:
        return RedirectResponse(url="/panel/", status_code=302)

    # Get tenants
    tenants_result = await db.execute(
        select(Tenant)
        .where(Tenant.project_id == project.id)
        .order_by(Tenant.created_at.desc())
    )
    tenants = tenants_result.scalars().all()

    # Check for new credentials in session
    credentials_html = ""
    if show_credentials and "project_credentials" in request.session:
        creds = request.session.pop("project_credentials", {})
        if creds.get("project_id") == project_id:
            credentials_html = f"""
            <div class="alert alert-warning mb-4">
                <h5><i class="fas fa-exclamation-triangle"></i> Credenciales Generadas</h5>
                <p class="mb-2"><strong>Guarda estas credenciales ahora. No se mostraran de nuevo.</strong></p>

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
                <a href="/panel/{project.id}/tenants/{tenant.id}" class="text-decoration-none">
                    <strong>{tenant.name}</strong>
                </a>
                <br><small class="text-muted">{tenant.slug}</small>
            </td>
            <td><code>{tenant.schema_name or 'N/A'}</code></td>
            <td>{status_badge}</td>
            <td>{tenant.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <a href="/panel/{project.id}/tenants/{tenant.id}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye"></i>
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
            <li class="breadcrumb-item"><a href="/panel/">Proyectos</a></li>
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
            <h6 class="mb-0"><i class="fas fa-code me-2"></i> Como usar en tu SaaS</h6>
        </div>
        <div class="card-body">
            <pre class="bg-dark text-light p-3 rounded mb-0"><code># 1. Obtener config del proyecto (JWT secret para firmar tokens)
curl -X GET http://localhost:8000/api/v1/auth/project \\
  -H "X-API-Key: TU_API_KEY"

# 2. Obtener info de un tenant
curl -X GET http://localhost:8000/api/v1/auth/tenant/mi-tenant \\
  -H "X-API-Key: TU_API_KEY"

# 3. Verificar un JWT (firmado por tu SaaS)
curl -X POST http://localhost:8000/api/v1/auth/verify \\
  -H "X-API-Key: TU_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{"token": "eyJhbGciOiJIUzI1NiIs..."}}'</code></pre>
        </div>
    </div>

    <!-- Tenants Section -->
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-building me-2"></i> Tenants</h5>
            <a href="/panel/{project_id}/tenants/create" class="btn btn-sm btn-success">
                <i class="fas fa-plus"></i> Nuevo Tenant
            </a>
        </div>
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Nombre</th>
                        <th>Schema</th>
                        <th>Estado</th>
                        <th>Creado</th>
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
        nav_users="",
        content=content
    )
    return HTMLResponse(content=html)


@router.get("/{project_id}/tenants/create", response_class=HTMLResponse)
async def create_tenant_form(request: Request, project_id: str, db: AsyncSession = Depends(get_db)):
    """Show create tenant form."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        return RedirectResponse(url="/panel/", status_code=302)

    result = await db.execute(
        select(Project).where(Project.id == project_uuid)
    )
    project = result.scalar_one_or_none()

    if not project:
        return RedirectResponse(url="/panel/", status_code=302)

    content = f"""
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/panel/">Proyectos</a></li>
            <li class="breadcrumb-item"><a href="/panel/{project_id}">{project.name}</a></li>
            <li class="breadcrumb-item active">Nuevo Tenant</li>
        </ol>
    </nav>

    <div class="card" style="max-width: 500px;">
        <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-building me-2"></i> Crear Tenant en {project.name}</h5>
        </div>
        <div class="card-body">
            <form method="POST" action="/panel/{project_id}/tenants/create">
                <div class="mb-3">
                    <label class="form-label">Nombre del Tenant *</label>
                    <input type="text" name="name" class="form-control" required
                           placeholder="Empresa ABC">
                    <div class="form-text">El slug se generara automaticamente</div>
                </div>

                <div class="alert alert-info">
                    <small>
                        <i class="fas fa-info-circle"></i>
                        Estrategia: <strong>{project.tenant_strategy}</strong>
                        {"- Se creara un schema PostgreSQL para este tenant" if project.tenant_strategy == "schema" else "- Se usara columna discriminadora"}
                    </small>
                </div>

                <hr>
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-success">
                        <i class="fas fa-save"></i> Crear Tenant
                    </button>
                    <a href="/panel/{project_id}" class="btn btn-outline-secondary">Cancelar</a>
                </div>
            </form>
        </div>
    </div>
    """

    html = BASE_TEMPLATE.format(
        title=f"Nuevo Tenant - {project.name}",
        nav_projects="active",
        nav_users="",
        content=content
    )
    return HTMLResponse(content=html)


@router.post("/{project_id}/tenants/create")
async def create_tenant(request: Request, project_id: str, db: AsyncSession = Depends(get_db)):
    """Create a tenant for a project."""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        return RedirectResponse(url="/panel/", status_code=302)

    result = await db.execute(
        select(Project).where(Project.id == project_uuid)
    )
    project = result.scalar_one_or_none()

    if not project:
        return RedirectResponse(url="/panel/", status_code=302)

    form = await request.form()
    name = form.get("name", "").strip()
    slug = python_slugify(name)

    # Check if slug exists in this project
    existing = await db.execute(
        select(Tenant).where(
            Tenant.project_id == project_uuid,
            Tenant.slug == slug
        )
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:8]}"

    # Create schema if needed
    schema_name = None
    if project.tenant_strategy == "schema":
        schema_name = f"tenant_{project.slug}_{slug}".replace("-", "_")
        await create_schema(schema_name)

    tenant = Tenant(
        project_id=project_uuid,
        name=name,
        slug=slug,
        schema_name=schema_name,
    )
    db.add(tenant)
    await db.commit()

    return RedirectResponse(
        url=f"/panel/{project_id}",
        status_code=302
    )


# ============================================================================
# Tenant Members & Invitations Routes
# ============================================================================

@router.get("/{project_id}/tenants/{tenant_id}", response_class=HTMLResponse)
async def view_tenant(request: Request, project_id: str, tenant_id: str, db: AsyncSession = Depends(get_db)):
    """View tenant with members and invitations."""
    try:
        project_uuid = uuid.UUID(project_id)
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        return RedirectResponse(url="/panel/", status_code=302)

    # Get tenant with project
    result = await db.execute(
        select(Tenant)
        .options(selectinload(Tenant.project))
        .where(Tenant.id == tenant_uuid, Tenant.project_id == project_uuid)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        return RedirectResponse(url=f"/panel/{project_id}", status_code=302)

    # Get members
    members_result = await db.execute(
        select(Membership)
        .options(selectinload(Membership.user))
        .where(Membership.tenant_id == tenant_uuid)
        .order_by(Membership.created_at.desc())
    )
    members = members_result.scalars().all()

    # Get invitations
    invitations_result = await db.execute(
        select(Invitation)
        .where(Invitation.tenant_id == tenant_uuid, Invitation.used_at.is_(None))
        .order_by(Invitation.created_at.desc())
    )
    invitations = invitations_result.scalars().all()

    # Build members table
    members_html = ""
    for m in members:
        status_badge = '<span class="badge bg-success">Activo</span>' if m.is_active else '<span class="badge bg-secondary">Inactivo</span>'
        roles_badges = " ".join([f'<span class="badge bg-primary">{r}</span>' for r in m.roles]) or '<span class="text-muted">Sin roles</span>'
        members_html += f"""
        <tr>
            <td>
                <a href="/panel/users/{m.user.id}" class="text-decoration-none">
                    <strong>{m.user.full_name}</strong>
                </a>
                <br><small class="text-muted">{m.user.email}</small>
            </td>
            <td>{roles_badges}</td>
            <td>{status_badge}</td>
            <td>{m.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <form method="POST" action="/panel/{project_id}/tenants/{tenant_id}/members/{m.user.id}/delete"
                      style="display:inline" onsubmit="return confirm('¿Eliminar este miembro?')">
                    <button type="submit" class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-trash"></i>
                    </button>
                </form>
            </td>
        </tr>
        """

    if not members:
        members_html = """
        <tr>
            <td colspan="5" class="text-center py-4">
                <p class="text-muted mb-0">No hay miembros en este tenant</p>
            </td>
        </tr>
        """

    # Build invitations table
    invitations_html = ""
    for inv in invitations:
        is_expired = datetime.utcnow() > inv.expires_at
        status_badge = '<span class="badge bg-danger">Expirada</span>' if is_expired else '<span class="badge bg-warning">Pendiente</span>'
        roles_badges = " ".join([f'<span class="badge bg-secondary">{r}</span>' for r in inv.roles]) or '<span class="text-muted">Sin roles</span>'
        invitations_html += f"""
        <tr>
            <td>{inv.email}</td>
            <td>{roles_badges}</td>
            <td>
                <code class="small">{inv.token[:20]}...</code>
                <i class="fas fa-copy copy-btn ms-2" style="cursor:pointer"
                   onclick="navigator.clipboard.writeText('{inv.token}'); this.className='fas fa-check text-success ms-2'"></i>
            </td>
            <td>{status_badge}</td>
            <td>{inv.expires_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <form method="POST" action="/panel/{project_id}/tenants/{tenant_id}/invitations/{inv.id}/delete"
                      style="display:inline" onsubmit="return confirm('¿Cancelar esta invitación?')">
                    <button type="submit" class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-trash"></i>
                    </button>
                </form>
            </td>
        </tr>
        """

    if not invitations:
        invitations_html = """
        <tr>
            <td colspan="6" class="text-center py-4">
                <p class="text-muted mb-0">No hay invitaciones pendientes</p>
            </td>
        </tr>
        """

    status_badge = '<span class="badge bg-success">Activo</span>' if tenant.is_active else '<span class="badge bg-secondary">Inactivo</span>'

    content = f"""
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/panel/">Proyectos</a></li>
            <li class="breadcrumb-item"><a href="/panel/{project_id}">{tenant.project.name}</a></li>
            <li class="breadcrumb-item active">{tenant.name}</li>
        </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
            <h2><i class="fas fa-building me-2"></i> {tenant.name}</h2>
            <p class="text-muted mb-0">Slug: <code>{tenant.slug}</code></p>
        </div>
        <div>
            {status_badge}
        </div>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card card-stats primary">
                <div class="card-body">
                    <h6 class="text-muted">Schema</h6>
                    <code>{tenant.schema_name or 'N/A'}</code>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stats success">
                <div class="card-body">
                    <h6 class="text-muted">Miembros</h6>
                    <span class="fs-4">{len(members)}</span>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-stats info">
                <div class="card-body">
                    <h6 class="text-muted">Invitaciones Pendientes</h6>
                    <span class="fs-4">{len(invitations)}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Members Section -->
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-users me-2"></i> Miembros</h5>
        </div>
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>Roles</th>
                        <th>Estado</th>
                        <th>Desde</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {members_html}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Invitations Section -->
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-envelope me-2"></i> Invitaciones Pendientes</h5>
            <button class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#inviteModal">
                <i class="fas fa-plus"></i> Nueva Invitación
            </button>
        </div>
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Roles</th>
                        <th>Token</th>
                        <th>Estado</th>
                        <th>Expira</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {invitations_html}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Invite Modal -->
    <div class="modal fade" id="inviteModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/panel/{project_id}/tenants/{tenant_id}/invite">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-envelope me-2"></i> Nueva Invitación</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Email *</label>
                            <input type="email" name="email" class="form-control" required
                                   placeholder="usuario@ejemplo.com">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Roles (separados por coma)</label>
                            <input type="text" name="roles" class="form-control"
                                   placeholder="admin, user">
                            <div class="form-text">Ejemplo: admin, editor, viewer</div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Expira en (horas)</label>
                            <input type="number" name="expires_hours" class="form-control"
                                   value="48" min="1" max="168">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-success">
                            <i class="fas fa-paper-plane"></i> Enviar Invitación
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    """

    html = BASE_TEMPLATE.format(
        title=f"{tenant.name} - {tenant.project.name}",
        nav_projects="active",
        nav_users="",
        content=content
    )
    return HTMLResponse(content=html)


@router.post("/{project_id}/tenants/{tenant_id}/invite")
async def create_invitation(request: Request, project_id: str, tenant_id: str, db: AsyncSession = Depends(get_db)):
    """Create an invitation for a tenant."""
    try:
        project_uuid = uuid.UUID(project_id)
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        return RedirectResponse(url="/panel/", status_code=302)

    # Verify tenant exists
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_uuid, Tenant.project_id == project_uuid)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        return RedirectResponse(url=f"/panel/{project_id}", status_code=302)

    form = await request.form()
    email = form.get("email", "").strip().lower()
    roles_str = form.get("roles", "").strip()
    expires_hours = int(form.get("expires_hours", 48))

    roles = [r.strip() for r in roles_str.split(",") if r.strip()] if roles_str else []

    invitation = Invitation(
        email=email,
        tenant_id=tenant_uuid,
        roles=roles,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    db.add(invitation)
    await db.commit()

    return RedirectResponse(
        url=f"/panel/{project_id}/tenants/{tenant_id}",
        status_code=302
    )


@router.post("/{project_id}/tenants/{tenant_id}/members/{user_id}/delete")
async def delete_member(request: Request, project_id: str, tenant_id: str, user_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a member from a tenant."""
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return RedirectResponse(url=f"/panel/{project_id}/tenants/{tenant_id}", status_code=302)

    result = await db.execute(
        select(Membership).where(
            Membership.tenant_id == tenant_uuid,
            Membership.user_id == user_uuid
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        await db.commit()

    return RedirectResponse(
        url=f"/panel/{project_id}/tenants/{tenant_id}",
        status_code=302
    )


@router.post("/{project_id}/tenants/{tenant_id}/invitations/{invitation_id}/delete")
async def delete_invitation(request: Request, project_id: str, tenant_id: str, invitation_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel an invitation."""
    try:
        invitation_uuid = uuid.UUID(invitation_id)
    except ValueError:
        return RedirectResponse(url=f"/panel/{project_id}/tenants/{tenant_id}", status_code=302)

    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_uuid)
    )
    invitation = result.scalar_one_or_none()
    if invitation:
        await db.delete(invitation)
        await db.commit()

    return RedirectResponse(
        url=f"/panel/{project_id}/tenants/{tenant_id}",
        status_code=302
    )
