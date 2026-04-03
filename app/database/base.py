from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.config import settings


# 1. Create the Engine
# Apply SQLite-specific fix only if needed
# 'check_same_thread=False' is specific to SQLite + FastAPI's concurrency
is_sqlite = settings.db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_async_engine(settings.db_url, connect_args=connect_args)

# 2. Create a Session factory
#   Set expire_on_commit=False based on sqlalchemy docs
#   Reference: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#asyncio-orm-avoid-lazyloads
SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

# 3. Base class for your models
#   Define the naming convention for all constraints
#   This prevents the "Constraint must have a name" error in SQLite/Alembic
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    All models will inherit from this class.
    This provides full type-safety for IDEs.
    """

    # Attach the convention to the metadata
    metadata = MetaData(naming_convention=naming_convention)


# 4. Dependency for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """
    Asynchronous generator that AsyncSession, provides a database session to FastAPI routes.
    The 'async with' block ensures the session is closed automatically.
    """
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            # While 'async with' handles closure,
            # explicitly awaiting ensures the connection returns to the pool.
            await db.close()
