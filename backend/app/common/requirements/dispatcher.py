from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RequirementEvent

from .registry import registry


async def dispatch_requirement_event(
    project_id: int,
    event: RequirementEvent,
    payload: dict,
    db: AsyncSession,
) -> None:
    """Route an event to every handler subscribed to it.

    Each handler's handle_event classmethod is responsible for idempotency
    and Decision #6's pristine-vs-progressed conditional rule on WA_CODE_REMOVED.
    First raising handler aborts the dispatch; caller owns the transaction.
    """
    for handler_cls in registry.handlers_for_event(event):
        await handler_cls.handle_event(project_id, event, payload, db)
