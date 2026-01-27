from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.admin import setup_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Sistema de Gestión de Proyectos SaaS

API para gestionar proyectos SaaS multi-tenant con autenticación centralizada.

### Características principales:
- **Gestión de Proyectos**: Crear y administrar proyectos SaaS
- **Multi-tenancy**: Soporte para aislamiento por schema o columna discriminadora
- **Autenticación Centralizada**: JWT con API Keys y OAuth2

### Flujos de Autenticación:

#### 1. API Key + Password
```
POST /api/v1/auth/token
Headers: X-API-Key: <your_api_key>
Body: { "email": "...", "password": "...", "tenant_slug": "..." }
```

#### 2. OAuth2 Client Credentials
```
POST /api/v1/auth/oauth/token
Body: {
  "grant_type": "password",
  "client_id": "...",
  "client_secret": "...",
  "username": "...",
  "password": "...",
  "tenant": "..."
}
```

#### 3. Validar Token
```
POST /api/v1/auth/validate
Headers: X-API-Key: <your_api_key>
Body: { "token": "<jwt_token>" }
```
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware (required for admin authentication)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Admin Panel
admin = setup_admin(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "admin": "/admin",
        "health": "/health",
    }
