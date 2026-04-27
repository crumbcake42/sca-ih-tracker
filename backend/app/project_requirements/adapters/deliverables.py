from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deliverables.models import (
    Deliverable,
    ProjectBuildingDeliverable,
    ProjectDeliverable,
)
from app.project_requirements.registry import register_requirement_type
from app.projects.services import _DERIVABLE_SCA_STATUSES


@register_requirement_type("deliverable")
class DeliverableRequirementAdapter:
    """
    Read-only adapter satisfying ``ProjectRequirement`` for ``ProjectDeliverable`` rows.

    Unfulfilled iff ``sca_status in _DERIVABLE_SCA_STATUSES`` — identical predicate to
    ``derive_project_status``'s outstanding_deliverable_count query (services.py:444).
    Deliverables are not dismissible in Session A; dismissibility arrives in Stage 3.
    """

    requirement_type = "deliverable"
    is_dismissable = False

    def __init__(self, row: ProjectDeliverable, deliverable: Deliverable) -> None:
        self._row = row
        self._deliverable = deliverable

    @property
    def project_id(self) -> int:
        return self._row.project_id

    @property
    def requirement_key(self) -> str:
        return str(self._row.deliverable_id)

    @property
    def label(self) -> str:
        return self._deliverable.name

    @property
    def is_dismissed(self) -> bool:
        return False

    def is_fulfilled(self) -> bool:
        return self._row.sca_status not in _DERIVABLE_SCA_STATUSES

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list["DeliverableRequirementAdapter"]:
        rows = (
            await db.execute(
                select(ProjectDeliverable, Deliverable)
                .join(Deliverable, ProjectDeliverable.deliverable_id == Deliverable.id)
                .where(
                    ProjectDeliverable.project_id == project_id,
                    ProjectDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES),
                )
            )
        ).all()
        return [cls(row, deliv) for row, deliv in rows]


@register_requirement_type("building_deliverable")
class BuildingDeliverableRequirementAdapter:
    """
    Read-only adapter satisfying ``ProjectRequirement`` for ``ProjectBuildingDeliverable`` rows.

    Same fulfilled predicate as ``DeliverableRequirementAdapter``.
    ``requirement_key`` encodes ``f"{deliverable_id}:{school_id}"`` to distinguish
    per-school rows for the same deliverable template.
    """

    requirement_type = "building_deliverable"
    is_dismissable = False

    def __init__(
        self, row: ProjectBuildingDeliverable, deliverable: Deliverable
    ) -> None:
        self._row = row
        self._deliverable = deliverable

    @property
    def project_id(self) -> int:
        return self._row.project_id

    @property
    def requirement_key(self) -> str:
        return f"{self._row.deliverable_id}:{self._row.school_id}"

    @property
    def label(self) -> str:
        return self._deliverable.name

    @property
    def is_dismissed(self) -> bool:
        return False

    def is_fulfilled(self) -> bool:
        return self._row.sca_status not in _DERIVABLE_SCA_STATUSES

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list["BuildingDeliverableRequirementAdapter"]:
        rows = (
            await db.execute(
                select(ProjectBuildingDeliverable, Deliverable)
                .join(
                    Deliverable,
                    ProjectBuildingDeliverable.deliverable_id == Deliverable.id,
                )
                .where(
                    ProjectBuildingDeliverable.project_id == project_id,
                    ProjectBuildingDeliverable.sca_status.in_(_DERIVABLE_SCA_STATUSES),
                )
            )
        ).all()
        return [cls(row, deliv) for row, deliv in rows]
