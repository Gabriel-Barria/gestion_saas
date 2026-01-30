from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Gestion SaaS"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gestion_saas"

    # Security (required in production - no defaults)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS - comma-separated origins (e.g., "http://localhost:3000,https://myapp.com")
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Admin credentials (required - no defaults)
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
