from typing import Literal

from .aggregator import get_unfulfilled_requirements_for_project
from .dispatcher import dispatch_requirement_event
from .protocol import DismissibleMixin, ManualTerminalMixin, ProjectRequirement
from .registry import RequirementTypeRegistry, register_requirement_type, registry
from .schemas import UnfulfilledRequirement

RequirementTypeName = Literal[
    "project_document",
    "contractor_payment_record",
    "lab_report",
    "project_dep_filing",
    "deliverable",
    "building_deliverable",
]

__all__ = [
    "get_unfulfilled_requirements_for_project",
    "dispatch_requirement_event",
    "ProjectRequirement",
    "DismissibleMixin",
    "ManualTerminalMixin",
    "register_requirement_type",
    "RequirementTypeRegistry",
    "registry",
    "UnfulfilledRequirement",
    "RequirementTypeName",
]