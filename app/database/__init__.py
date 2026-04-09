# Import all app models here so they're registered by Base.
# These imports are intentionally "unused" — the act of importing them
# causes SQLAlchemy to register the models against Base.metadata.
from app.contractors import models as contractor_models  # noqa: F401
from app.deliverables import models as deliverable_models  # noqa: F401
from app.employees import models as employee_models  # noqa: F401
from app.hygienists import models as hygienist_models  # noqa: F401
from app.projects import models as project_models  # noqa: F401
from app.schools import models as school_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.wa_codes import models as wa_code_models  # noqa: F401

from .base import Base, SessionLocal, engine, get_db
from .mixins import AuditMixin

__all__ = ["Base", "SessionLocal", "get_db", "engine", "AuditMixin"]
