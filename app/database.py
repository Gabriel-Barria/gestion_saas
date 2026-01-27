from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_schema(schema_name: str) -> None:
    """Create a new PostgreSQL schema for tenant isolation."""
    async with async_session_maker() as session:
        await session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        await session.commit()


async def drop_schema(schema_name: str) -> None:
    """Drop a PostgreSQL schema."""
    async with async_session_maker() as session:
        await session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        await session.commit()
