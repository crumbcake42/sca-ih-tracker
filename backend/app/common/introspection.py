from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import ColumnProperty

from app.database.mixins import AuditMixin

# Derive excluded field names directly from AuditMixin so additions there are
# automatically picked up without touching this file.
_AUDIT_FIELDS: frozenset[str] = frozenset(AuditMixin.__annotations__)


def filterable_columns(model: type) -> dict[str, Any]:
    """Return {attr_name: Column} for scalar columns on *model*.

    Excludes AuditMixin fields and columns whose SQLAlchemy type has no
    Python equivalent (e.g. NullType).  Called once at factory construction
    time, not per-request.
    """
    mapper = sa_inspect(model)
    result: dict[str, Any] = {}
    for prop in mapper.iterate_properties:
        if not isinstance(prop, ColumnProperty):
            continue
        if prop.key in _AUDIT_FIELDS:
            continue
        if len(prop.columns) != 1:
            continue
        col = prop.columns[0]
        try:
            col.type.python_type
        except NotImplementedError:
            continue
        result[prop.key] = col
    return result
