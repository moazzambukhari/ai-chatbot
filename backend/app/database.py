from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    # Import models so metadata is populated before create_all.
    from app import models  # noqa: F401

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except OSError as exc:
        raise RuntimeError(
            "Could not connect to PostgreSQL. Start it with "
            "`docker compose -f backend/docker-compose.yml up -d` "
            f"and confirm DATABASE_URL is correct. Original error: {exc}"
        ) from exc
