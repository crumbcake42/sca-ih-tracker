from pydantic import BaseModel


class UnfulfilledRequirement(BaseModel):
    """Uniform schema returned by the closure-gate aggregator for any requirement type."""

    requirement_type: str
    project_id: int
    # Opaque stable identifier scoped to (requirement_type, project_id).
    # Deliverable: str(deliverable_id); building deliverable: f"{deliverable_id}:{school_id}".
    # Per-type endpoints introduced in later sessions parse this value.
    requirement_key: str
    label: str
    is_dismissed: bool
    is_dismissable: bool
