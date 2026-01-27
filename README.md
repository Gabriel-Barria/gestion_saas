# Gestion SaaS - Servicio de Gestión Multi-Tenant

Sistema centralizado para gestionar proyectos SaaS multi-tenant. Este servicio administra **Proyectos** y **Tenants**, proporcionando a cada proyecto SaaS las credenciales necesarias para implementar su propia autenticación.

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    GESTION SAAS                         │
│           (Este servicio - gestión central)             │
├─────────────────────────────────────────────────────────┤
│  Panel de Gestión (/panel/)                             │
│  └── Crear/gestionar proyectos y tenants                │
├─────────────────────────────────────────────────────────┤
│  API de Autenticación (/api/v1/auth/)                   │
│  ├── GET  /project         → JWT secret para firmar     │
│  ├── GET  /tenant/{slug}   → Info del tenant            │
│  ├── POST /verify          → Verificar firma JWT        │
│  └── GET  /verify          → Verificar via Bearer       │
└─────────────────────────────────────────────────────────┘
                            │
                            │ Cada proyecto SaaS consume
                            │ esta API para:
                            │ - Obtener JWT secret
                            │ - Resolver tenant slugs
                            │ - Verificar tokens
                            ▼
┌─────────────────────────────────────────────────────────┐
│              TU PROYECTO SAAS                           │
│         (Tu aplicación - maneja usuarios)               │
├─────────────────────────────────────────────────────────┤
│  - Almacena usuarios en TU base de datos                │
│  - Firma JWTs con el secret de este servicio            │
│  - Implementa login/registro de usuarios                │
│  - Gestiona permisos y roles                            │
└─────────────────────────────────────────────────────────┘
```

## Conceptos Clave

- **Proyecto**: Representa tu aplicación SaaS. Contiene las credenciales (API Key, JWT Secret).
- **Tenant**: Una instancia/cliente dentro de tu proyecto. Identificado por slug (ej: `empresa-abc`).
- **Usuarios**: **NO se gestionan aquí**. Cada proyecto SaaS almacena sus propios usuarios.

## Documentación API

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Endpoints de Autenticación

Todos los endpoints requieren el header `X-API-Key` con la API Key de tu proyecto.

### 1. Obtener Información del Proyecto

Obtén el JWT secret y configuración para firmar tokens en tu aplicación.

```bash
curl -X GET http://localhost:8000/api/v1/auth/project \
  -H "X-API-Key: TU_API_KEY"
```

**Respuesta:**
```json
{
  "id": "uuid-del-proyecto",
  "name": "Mi Proyecto SaaS",
  "slug": "mi-proyecto",
  "tenant_strategy": "schema",
  "jwt_secret": "tu-jwt-secret-para-firmar-tokens",
  "jwt_algorithm": "HS256",
  "jwt_expiration_minutes": 30
}
```

### 2. Obtener Información del Tenant

Resuelve un slug de tenant a su ID y metadata.

```bash
curl -X GET http://localhost:8000/api/v1/auth/tenant/mi-tenant \
  -H "X-API-Key: TU_API_KEY"
```

**Respuesta:**
```json
{
  "id": "uuid-del-tenant",
  "name": "Mi Tenant",
  "slug": "mi-tenant",
  "schema_name": "tenant_mi_tenant",
  "is_active": true
}
```

### 3. Verificar Token JWT (POST)

Verifica que un token fue firmado con el secret de tu proyecto.

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "X-API-Key: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

**Respuesta exitosa:**
```json
{
  "valid": true,
  "payload": {
    "sub": "user-id",
    "email": "usuario@ejemplo.com",
    "tenant_id": "tenant-uuid",
    "exp": 1234567890
  },
  "error": null
}
```

**Respuesta con error:**
```json
{
  "valid": false,
  "payload": null,
  "error": "Invalid or expired token"
}
```

### 4. Verificar Token JWT (GET con Bearer)

Alternativa que lee el token del header Authorization.

```bash
curl -X GET http://localhost:8000/api/v1/auth/verify \
  -H "X-API-Key: TU_API_KEY" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Integración en tu Aplicación SaaS

### Flujo Recomendado

1. **Al iniciar tu app**: Obtén el JWT secret llamando a `GET /api/v1/auth/project`
2. **Login de usuario**: Valida credenciales en TU base de datos y firma un JWT con el secret
3. **Requests autenticados**: Verifica el JWT localmente o usa `POST /api/v1/auth/verify`
4. **Multi-tenancy**: Usa `GET /api/v1/auth/tenant/{slug}` para resolver slugs a IDs

### Python (ejemplo completo)

```python
import requests
import jwt
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"
API_KEY = "tu_api_key"

# 1. Obtener configuración JWT del proyecto
response = requests.get(
    f"{API_URL}/api/v1/auth/project",
    headers={"X-API-Key": API_KEY}
)
project = response.json()
JWT_SECRET = project["jwt_secret"]
JWT_ALGORITHM = project["jwt_algorithm"]
JWT_EXPIRATION = project["jwt_expiration_minutes"]

# 2. Cuando un usuario hace login en TU sistema
def login_user(email: str, password: str, tenant_slug: str):
    # Valida credenciales en TU base de datos
    user = validate_user_in_your_db(email, password, tenant_slug)
    if not user:
        raise Exception("Invalid credentials")

    # Firma el JWT con el secret del servicio central
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "roles": user.roles,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# 3. Verificar token (opción A: localmente)
def verify_token_local(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        return None

# 4. Verificar token (opción B: via API)
def verify_token_api(token: str):
    response = requests.post(
        f"{API_URL}/api/v1/auth/verify",
        headers={"X-API-Key": API_KEY},
        json={"token": token}
    )
    result = response.json()
    return result["payload"] if result["valid"] else None

# 5. Resolver tenant slug a ID
def get_tenant_info(tenant_slug: str):
    response = requests.get(
        f"{API_URL}/api/v1/auth/tenant/{tenant_slug}",
        headers={"X-API-Key": API_KEY}
    )
    return response.json()
```

### JavaScript/Node.js

```javascript
const jwt = require('jsonwebtoken');

const API_URL = "http://localhost:8000";
const API_KEY = "tu_api_key";

// 1. Obtener configuración JWT
async function getProjectConfig() {
  const response = await fetch(`${API_URL}/api/v1/auth/project`, {
    headers: { "X-API-Key": API_KEY }
  });
  return response.json();
}

// 2. Firmar JWT para un usuario
async function createUserToken(user, projectConfig) {
  const payload = {
    sub: user.id,
    email: user.email,
    tenant_id: user.tenantId,
    roles: user.roles
  };

  return jwt.sign(payload, projectConfig.jwt_secret, {
    algorithm: projectConfig.jwt_algorithm,
    expiresIn: `${projectConfig.jwt_expiration_minutes}m`
  });
}

// 3. Verificar token via API
async function verifyToken(token) {
  const response = await fetch(`${API_URL}/api/v1/auth/verify`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ token })
  });
  return response.json();
}

// 4. Obtener info del tenant
async function getTenantInfo(tenantSlug) {
  const response = await fetch(`${API_URL}/api/v1/auth/tenant/${tenantSlug}`, {
    headers: { "X-API-Key": API_KEY }
  });
  return response.json();
}
```

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - API Key inválida o proyecto inactivo |
| 404 | Not Found - Tenant no encontrado |

**Ejemplo de error:**
```json
{
  "detail": "Invalid API key"
}
```

## Panel de Gestión

El panel en `/panel/` es de **uso interno** para:
- Crear y gestionar proyectos
- Crear tenants dentro de cada proyecto
- Ver credenciales (API Key, Client ID/Secret) al crear un proyecto

## Ejecutar Localmente

```bash
# Clonar repositorio
git clone https://github.com/Gabriel-Barria/gestion_saas.git
cd gestion_saas

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# Aplicar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

## Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| DATABASE_URL | URL de conexión PostgreSQL | Si |
| SECRET_KEY | Clave secreta para sesiones | Si |
| ADMIN_EMAIL | Email del admin del panel | Si |
| ADMIN_PASSWORD | Password del admin del panel | Si |

## Tecnologias

- **Python 3.12** + **FastAPI**
- **PostgreSQL 15** + **SQLAlchemy 2.0**
- **JWT** (python-jose)
- **Alembic** (migraciones)
