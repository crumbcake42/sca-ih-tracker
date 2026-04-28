from datetime import datetime
from typing import ClassVar, Protocol, runtime_checkable

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column


@runtime_checkable
class ProjectRequirement(Protocol):
    """
    Structural protocol that every requirement type must expose.

    Adapters do not inherit this class — they satisfy it structurally.
    Use ``isinstance(obj, ProjectRequirement)`` only as a contract gate in tests;
    production code drives behaviour through the registry, not isinstance checks.

    Note: ``template_params_model`` is a handler-class attribute, not a requirement
    instance attribute — it is not part of this Protocol.
    """

    project_id: int
    requirement_type: str
    label: str
    is_dismissable: bool
    is_dismissed: bool

    def is_fulfilled(self) -> bool: ...


@declarative_mixin
class DismissibleMixin:
    """
    SQLAlchemy declarative mixin for requirement tables that support manager dismissal.

    Defined in Session A; no model inherits it yet — first consumer is Session C.
    Inheriting this mixin adds three columns; each inheritor must include a migration.
    """

    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dismissed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ManualTerminalMixin:
    """
    Marker for requirement types whose state can reach manual terminal values
    that are immune to automatic recalculation (e.g. CPR RFA/RFP stages).

    Silo models inherit this; the aggregator can detect it via
    ``isinstance(handler_cls, type) and getattr(handler_cls, 'has_manual_terminals', False)``.
    """

    has_manual_terminals: ClassVar[bool] = True
