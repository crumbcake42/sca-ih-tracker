from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import SYSTEM_USER_ID
from app.common.enums import RequirementEvent
from app.common.requirements import register_requirement_type
from app.lab_reports.models import LabReportRequirement


@register_requirement_type("lab_report", events=[RequirementEvent.BATCH_CREATED])
class LabReportHandler:
    """Registry handler for Silo 4 lab report requirements.

    One LabReportRequirement is auto-materialized per SampleBatch on BATCH_CREATED.
    Materialization is idempotent: re-dispatching for the same batch creates no duplicate.
    """

    requirement_type: ClassVar[str] = "lab_report"
    is_dismissable: ClassVar[bool] = True

    @classmethod
    def validate_template_params(cls, params: dict) -> None:
        if params:
            raise ValueError(
                "lab_report requirements are not configurable via requirement-triggers; "
                "they are created automatically on batch creation"
            )

    @classmethod
    async def handle_event(
        cls, project_id: int, event: RequirementEvent, payload: dict, db: AsyncSession
    ) -> None:
        if event != RequirementEvent.BATCH_CREATED:
            return
        batch_id = payload["batch_id"]
        existing = (
            await db.execute(
                select(LabReportRequirement).where(
                    LabReportRequirement.sample_batch_id == batch_id,
                    LabReportRequirement.dismissed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(LabReportRequirement(
                project_id=project_id,
                sample_batch_id=batch_id,
                created_by_id=SYSTEM_USER_ID,
            ))

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list[LabReportRequirement]:
        return list(
            (
                await db.execute(
                    select(LabReportRequirement).where(
                        LabReportRequirement.project_id == project_id,
                        LabReportRequirement.is_saved.is_(False),
                        LabReportRequirement.dismissed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
