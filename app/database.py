import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from sqlalchemy.orm import DeclarativeBase


# 1. Define the path to your local data folder
# This ensures it finds the /data/ folder relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'dev.db')}"

# 2. Ensure the data directory exists (avoids "Folder Not Found" errors)
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# 3. Create the Engine
# 'check_same_thread=False' is specific to SQLite + FastAPI's concurrency
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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
