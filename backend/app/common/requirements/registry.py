from collections.abc import Iterable

from app.common.enums import RequirementEvent


class RequirementTypeRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, type] = {}
        self._events: dict[RequirementEvent, list[type]] = {}

    def register(
        self, name: str, handler: type, events: list[RequirementEvent] | None = None
    ) -> None:
        if name in self._handlers:
            raise ValueError(
                f"Requirement type '{name}' is already registered by {self._handlers[name]!r}."
            )
        self._handlers[name] = handler
        for event in events or []:
            self._events.setdefault(event, []).append(handler)

    def get(self, name: str) -> type:
        try:
            return self._handlers[name]
        except KeyError:
            raise KeyError(f"Unknown requirement type: '{name}'") from None

    def all_handlers(self) -> Iterable[type]:
        return self._handlers.values()

    def handlers_for_event(self, event: RequirementEvent) -> list[type]:
        return self._events.get(event, [])

    def clear(self) -> None:
        self._handlers.clear()
        self._events.clear()


registry = RequirementTypeRegistry()


def register_requirement_type(
    name: str,
    events: list[RequirementEvent] | None = None,
):
    """Class decorator that registers the decorated class in the global registry."""

    def decorator(cls: type) -> type:
        registry.register(name, cls, events=events)
        return cls

    return decorator
