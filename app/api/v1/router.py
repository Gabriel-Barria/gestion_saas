from fastapi import APIRouter

from app.api.v1 import projects, tenants, auth, users

api_router = APIRouter()

api_router.include_router(projects.router)
api_router.include_router(tenants.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
