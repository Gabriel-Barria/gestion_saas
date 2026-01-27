# Gestion SaaS - API de Autenticacion Multi-Tenant

API centralizada para gestionar autenticacion en proyectos SaaS multi-tenant.

## Que hace este servicio

Este servicio proporciona a tu proyecto SaaS:
- **JWT Secret** para firmar tokens de autenticacion
- **Informacion de Tenants** para resolver slugs a IDs
- **Verificacion de JWT** para validar tokens firmados

**Importante:** Los usuarios se gestionan en TU base de datos, no aqui. Este servicio solo proporciona las credenciales y utilidades de autenticacion.

## Endpoints

Todos los endpoints requieren el header `X-API-Key`.

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/api/v1/auth/project` | Obtener JWT secret y configuracion |
| GET | `/api/v1/auth/tenant/{slug}` | Obtener informacion del tenant |
| POST | `/api/v1/auth/verify` | Verificar firma de un JWT |
| GET | `/api/v1/auth/verify` | Verificar JWT via header Bearer |

## Uso

### 1. Obtener configuracion del proyecto

```bash
curl -X GET http://localhost:8000/api/v1/auth/project \
  -H "X-API-Key: TU_API_KEY"
```

**Respuesta:**
```json
{
  "id": "uuid",
  "name": "Mi Proyecto",
  "slug": "mi-proyecto",
  "jwt_secret": "secret-para-firmar-tokens",
  "jwt_algorithm": "HS256",
  "jwt_expiration_minutes": 30
}
```

### 2. Obtener informacion del tenant

```bash
curl -X GET http://localhost:8000/api/v1/auth/tenant/empresa-abc \
  -H "X-API-Key: TU_API_KEY"
```

**Respuesta:**
```json
{
  "id": "uuid",
  "name": "Empresa ABC",
  "slug": "empresa-abc",
  "schema_name": "tenant_empresa_abc",
  "is_active": true
}
```

### 3. Verificar un token JWT

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "X-API-Key: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJIUzI1NiIs..."}'
```

**Respuesta:**
```json
{
  "valid": true,
  "payload": {
    "sub": "user-id",
    "email": "usuario@ejemplo.com",
    "tenant_id": "tenant-uuid"
  },
  "error": null
}
```

## Integracion

### Python

```python
import requests
import jwt
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"
API_KEY = "tu_api_key"

# Obtener configuracion
response = requests.get(
    f"{API_URL}/api/v1/auth/project",
    headers={"X-API-Key": API_KEY}
)
config = response.json()

# Firmar JWT para un usuario de TU sistema
def create_token(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "exp": datetime.utcnow() + timedelta(minutes=config["jwt_expiration_minutes"])
    }
    return jwt.encode(payload, config["jwt_secret"], algorithm=config["jwt_algorithm"])

# Verificar token
def verify_token(token):
    response = requests.post(
        f"{API_URL}/api/v1/auth/verify",
        headers={"X-API-Key": API_KEY},
        json={"token": token}
    )
    return response.json()
```

### JavaScript

```javascript
const API_URL = "http://localhost:8000";
const API_KEY = "tu_api_key";

// Obtener configuracion
async function getConfig() {
  const res = await fetch(`${API_URL}/api/v1/auth/project`, {
    headers: { "X-API-Key": API_KEY }
  });
  return res.json();
}

// Verificar token
async function verifyToken(token) {
  const res = await fetch(`${API_URL}/api/v1/auth/verify`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ token })
  });
  return res.json();
}
```

## Errores

| Codigo | Descripcion |
|--------|-------------|
| 401 | API Key invalida o proyecto inactivo |
| 404 | Tenant no encontrado |

```json
{
  "detail": "Invalid API key"
}
```

## Documentacion interactiva

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
