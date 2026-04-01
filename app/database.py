import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.common.config import settings

from sqlalchemy import create_engine
from app.common.config import settings


# 1. Define the path to your local data folder
# This ensures it finds the /data/ folder relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 3. Create the Engine
# Apply SQLite-specific fix only if needed
# 'check_same_thread=False' is specific to SQLite + FastAPI's concurrency
is_sqlite = settings.db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(settings.db_url, connect_args=connect_args)

# 4. Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 5. Base class for your models
class Base(DeclarativeBase):
    """
    All models will inherit from this class.
    This provides full type-safety for IDEs.
    """

    pass


# 6. Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
