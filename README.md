# Gestion SaaS - API de Autenticacion Multi-Tenant

API centralizada para gestionar autenticacion en proyectos SaaS multi-tenant.

## Que hace este servicio

Este servicio proporciona:
- **Sistema de Usuarios Global**: Un usuario, multiples tenants/proyectos
- **JWT Secret** para firmar tokens de autenticacion
- **Informacion de Tenants** para resolver slugs a IDs
- **Verificacion de JWT** para validar tokens firmados
- **Sistema de Invitaciones** para agregar usuarios a tenants

## Modelo de Identidad Hibrido

```
Usuario (identidad global)
    |
    +-- Membership --> Tenant A (proyecto 1) [roles: admin]
    |
    +-- Membership --> Tenant B (proyecto 1) [roles: user]
    |
    +-- Membership --> Tenant C (proyecto 2) [roles: admin]
```

Un usuario puede:
- Pertenecer a multiples tenants del mismo proyecto
- Pertenecer a tenants de diferentes proyectos
- Tener diferentes roles en cada tenant

## Endpoints

### Autenticacion Global (sin API Key)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar usuario |
| POST | `/auth/login` | Login global (retorna memberships) |
| POST | `/auth/login/tenant` | Login a tenant (retorna JWT) |
| POST | `/auth/refresh` | Renovar access token |
| GET | `/auth/invitations/{token}` | Info de invitacion |
| POST | `/auth/invitations/accept` | Aceptar invitacion |

### Usuarios Autenticados (requieren JWT)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/users/me` | Mi perfil |
| PUT | `/users/me` | Actualizar perfil |
| PUT | `/users/me/password` | Cambiar contrasena |
| GET | `/users/me/memberships` | Mis memberships |

### Operaciones SaaS (requieren API Key)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/auth/project` | Obtener JWT secret y configuracion |
| GET | `/auth/tenant/{slug}` | Obtener informacion del tenant |
| POST | `/auth/verify` | Verificar firma de un JWT |

### Gestion de Miembros (requieren API Key)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/tenants/{id}/members` | Listar miembros |
| PUT | `/tenants/{id}/members/{user_id}` | Actualizar roles |
| DELETE | `/tenants/{id}/members/{user_id}` | Remover miembro |
| GET | `/tenants/{id}/invitations` | Listar invitaciones |
| POST | `/tenants/{id}/invitations` | Crear invitacion |
| DELETE | `/tenants/{id}/invitations/{id}` | Cancelar invitacion |

## Flujos de Uso

### Flujo 1: Login Global con Seleccion de Tenant

```bash
# 1. Login global
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "mi_password"}'

# Respuesta: usuario + lista de tenants disponibles
# {
#   "user_id": "uuid",
#   "email": "usuario@ejemplo.com",
#   "memberships": [
#     {"tenant_id": "uuid", "tenant_name": "Empresa A", "roles": ["admin"]},
#     {"tenant_id": "uuid", "tenant_name": "Empresa B", "roles": ["user"]}
#   ]
# }

# 2. Usuario selecciona tenant -> Login a tenant especifico
curl -X POST http://localhost:8000/api/v1/auth/login/tenant \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "mi_password", "tenant_id": "tenant-uuid"}'

# Respuesta: JWT tokens
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "expires_in": 1800
# }
```

### Flujo 2: Invitar Usuario a Tenant

```bash
# 1. Admin crea invitacion
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/tenants/{tenant_id}/invitations \
  -H "Content-Type: application/json" \
  -d '{"email": "nuevo@ejemplo.com", "roles": ["user"]}'

# Respuesta incluye token
# {"token": "abc123...", "expires_at": "..."}

# 2. Usuario acepta invitacion (si no tiene cuenta, debe proporcionar password)
curl -X POST http://localhost:8000/api/v1/auth/invitations/accept \
  -H "Content-Type: application/json" \
  -d '{"token": "abc123...", "password": "mi_password", "full_name": "Nuevo Usuario"}'
```

### Flujo 3: SaaS Verifica Token

```bash
# El SaaS recibe un JWT de su frontend y lo verifica
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "X-API-Key: API_KEY_DEL_PROYECTO" \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJ..."}'

# Respuesta
# {
#   "valid": true,
#   "payload": {
#     "sub": "user-uuid",
#     "email": "usuario@ejemplo.com",
#     "tenant_id": "tenant-uuid",
#     "roles": ["admin"]
#   }
# }
```

## Estructura del JWT

```json
{
  "sub": "user-uuid",
  "email": "usuario@ejemplo.com",
  "tenant_id": "tenant-uuid",
  "project_id": "project-uuid",
  "roles": ["admin", "user"],
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

## Integracion para SaaS

### Opcion A: Usar Login Global

Tu SaaS puede usar los endpoints de login global. Flujo recomendado:

1. Frontend llama a `POST /auth/login` con credenciales
2. Si hay multiples tenants, mostrar selector
3. Frontend llama a `POST /auth/login/tenant` con tenant seleccionado
4. Backend recibe JWT y lo verifica con `POST /auth/verify` usando API Key

### Opcion B: Login Propio + Verificacion

Si prefieres manejar el login en tu propio backend:

1. Obtener JWT secret con `GET /auth/project` (una vez, cachear)
2. Tu backend firma JWTs directamente
3. Verificar tokens con `POST /auth/verify` o localmente con el secret

## Errores

| Codigo | Descripcion |
|--------|-------------|
| 400 | Request invalido (email duplicado, password muy corto, etc.) |
| 401 | Credenciales invalidas o token expirado |
| 403 | Sin permisos para la operacion |
| 404 | Recurso no encontrado |

```json
{
  "detail": "Invalid email or password"
}
```

## Documentacion interactiva

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Panel Admin: `http://localhost:8000/panel/`
