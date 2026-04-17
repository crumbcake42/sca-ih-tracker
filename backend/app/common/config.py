from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The absolute root of your project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # --- DATABASE SETTINGS ---
    # Primary connection string (e.g., PostgreSQL for Cloud SQL).
    # If set, LOCAL_DATABASE_PATH is ignored.
    DATABASE_URL: str | None = Field(default=None, alias="DATABASE_URL")

    # Fallback path for SQLite (Local Dev).
    # Relative to PROJECT_ROOT.
    LOCAL_DATABASE_PATH: str = "data/dev.db"

    # --- SECURITY & AUTHENTICATION ---
    # Key used to sign JWT tokens. MUST be kept secret in production.
    # Generate via: openssl rand -hex 32
    SECRET_KEY: str = "your-super-secret-key-here"

    # Hashing algorithm for JWT (HS256 is standard)
    ALGORITHM: str = "HS256"

    # How long a user stays logged in before needing a new token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- INITIAL SETUP CREDENTIALS ---
    # Used by app/scripts/db.py to seed the first SuperAdmin
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_EMAIL: str = "admin@agency.gov"
    FIRST_ADMIN_PASSWORD: str = "changeme"

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- FRONTEND URL FOR CORS WHITELISTING ---
    FRONTEND_DEV_URL: str ="http://127.0.0.1:3001"


    @property
    def db_url(self) -> str:
        """
        Returns a valid SQLAlchemy connection string.
        Prioritizes DATABASE_URL, falls back to LOCAL_DATABASE_PATH.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        abs_path = PROJECT_ROOT / self.LOCAL_DATABASE_PATH
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{abs_path}"


settings = Settings()

# Reserved user ID for system-initiated writes (quick-add, status recalculation, etc.)
# This row is inserted first in db.initialize() so it naturally receives id=1.
SYSTEM_USER_ID: int = 1
