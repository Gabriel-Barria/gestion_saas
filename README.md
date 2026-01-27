# Gestion SaaS - Servicio de Autenticación Centralizada

Sistema centralizado de autenticación para proyectos SaaS multi-tenant.

## Descripción

Este servicio proporciona autenticación centralizada para múltiples proyectos SaaS. Cada proyecto puede tener múltiples tenants (clientes), y cada tenant tiene sus propios usuarios.

**Nota:** El panel de gestión (`/panel/`) es de uso interno. Este documento describe cómo consumir la API de autenticación desde sistemas externos.

## Documentación API

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Autenticación

Para consumir este servicio necesitas las credenciales de tu proyecto:
- **API Key** - Para autenticación via header
- **Client ID** y **Client Secret** - Para autenticación OAuth2

### Método 1: API Key + Password

Obtén un token JWT enviando las credenciales del usuario con tu API Key.

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "X-API-Key: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "contraseña",
    "tenant_slug": "mi-tenant"
  }'
```

**Respuesta exitosa:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Método 2: OAuth2 (Client Credentials + Password)

Alternativa usando OAuth2 estándar.

```bash
curl -X POST http://localhost:8000/api/v1/auth/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "client_id": "TU_CLIENT_ID",
    "client_secret": "TU_CLIENT_SECRET",
    "username": "usuario@ejemplo.com",
    "password": "contraseña",
    "tenant": "mi-tenant"
  }'
```

**Respuesta exitosa:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Validar Token

Verifica si un token es válido y obtén información del usuario.

```bash
curl -X POST http://localhost:8000/api/v1/auth/validate \
  -H "X-API-Key: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Respuesta exitosa:**
```json
{
  "valid": true,
  "user": {
    "id": "uuid",
    "email": "usuario@ejemplo.com",
    "full_name": "Nombre Usuario",
    "roles": ["admin", "user"]
  },
  "tenant": {
    "id": "uuid",
    "name": "Mi Tenant",
    "slug": "mi-tenant"
  },
  "project": {
    "id": "uuid",
    "name": "Mi Proyecto",
    "slug": "mi-proyecto"
  }
}
```

### Refresh Token

Renueva el access token usando el refresh token.

```bash
curl -X POST http://localhost:8000/api/v1/auth/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "refresh_token",
    "client_id": "TU_CLIENT_ID",
    "client_secret": "TU_CLIENT_SECRET",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## Estructura del Token JWT

El token JWT contiene los siguientes claims:

```json
{
  "sub": "user_id",
  "email": "usuario@ejemplo.com",
  "tenant_id": "tenant_uuid",
  "tenant_slug": "mi-tenant",
  "project_id": "project_uuid",
  "roles": ["admin", "user"],
  "exp": 1234567890,
  "iat": 1234567890
}
```

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - Credenciales inválidas o token expirado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Proyecto, tenant o usuario no encontrado |

**Ejemplo de error:**
```json
{
  "detail": "Invalid credentials"
}
```

## Integración en tu Aplicación

### Python (requests)

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "tu_api_key"

# Obtener token
response = requests.post(
    f"{API_URL}/api/v1/auth/token",
    headers={"X-API-Key": API_KEY},
    json={
        "email": "usuario@ejemplo.com",
        "password": "contraseña",
        "tenant_slug": "mi-tenant"
    }
)
token = response.json()["access_token"]

# Validar token
response = requests.post(
    f"{API_URL}/api/v1/auth/validate",
    headers={"X-API-Key": API_KEY},
    json={"token": token}
)
user_info = response.json()
```

### JavaScript (fetch)

```javascript
const API_URL = "http://localhost:8000";
const API_KEY = "tu_api_key";

// Obtener token
const loginResponse = await fetch(`${API_URL}/api/v1/auth/token`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    email: "usuario@ejemplo.com",
    password: "contraseña",
    tenant_slug: "mi-tenant"
  })
});
const { access_token } = await loginResponse.json();

// Validar token
const validateResponse = await fetch(`${API_URL}/api/v1/auth/validate`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ token: access_token })
});
const userInfo = await validateResponse.json();
```

## Ejecutar con Docker

```bash
# Clonar repositorio
git clone https://github.com/Gabriel-Barria/gestion_saas.git
cd gestion_saas

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f app
```

El servicio estará disponible en:
- API: `http://localhost:8000`
- Documentación: `http://localhost:8000/docs`

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| DATABASE_URL | URL de conexión PostgreSQL | - |
| SECRET_KEY | Clave secreta para sesiones | - |
| ADMIN_EMAIL | Email del admin del panel | - |
| ADMIN_PASSWORD | Password del admin del panel | - |

## Tecnologías

- **Python 3.12** + **FastAPI**
- **PostgreSQL 15** + **SQLAlchemy 2.0**
- **JWT** (python-jose)
- **Docker** + **Docker Compose**
