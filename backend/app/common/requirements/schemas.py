from pydantic import BaseModel


class UnfulfilledRequirement(BaseModel):
    """Uniform schema returned by the closure-gate aggregator for any requirement type."""

    requirement_type: str
    project_id: int
    label: str
    is_dismissed: bool
    is_dismissable: bool
