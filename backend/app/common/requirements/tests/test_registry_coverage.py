"""
Registry coverage test.

Walks SQLAlchemy's mapper registry and asserts that every ORM model declaring
a `requirement_type: ClassVar[str]` has a corresponding handler registered
under that name in the requirement registry.

Catches the "added a silo ORM model but forgot to register the handler" failure
mode before it reaches production (where the materializer would silently no-op).
"""

import app.cprs  # noqa: F401 — side-effect: registers ContractorPaymentRecordHandler
import app.deliverables.requirement_adapter  # noqa: F401 — side-effect: registers deliverable adapters
import app.required_docs  # noqa: F401 — side-effect: registers ProjectDocumentHandler
from app.common.requirements import registry
from app.database import Base


def test_every_model_with_requirement_type_classvar_is_registered():
    registered_names = set(registry._handlers.keys())
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        rtype = getattr(cls, "requirement_type", None)
        if not isinstance(rtype, str):
            continue
        assert rtype in registered_names, (
            f"Model {cls.__name__} declares requirement_type={rtype!r} "
            f"but no handler is registered under that name. "
            f"Add @register_requirement_type('{rtype}') to its handler class "
            f"and import it as a side effect in its module's __init__.py."
        )
