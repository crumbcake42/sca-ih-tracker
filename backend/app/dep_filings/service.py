from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RequirementEvent
from app.common.requirements import register_requirement_type
from app.dep_filings.models import ProjectDEPFiling


async def materialize_for_form_selection(
    project_id: int, form_ids: list[int], current_user_id: int, db: AsyncSession
) -> list[ProjectDEPFiling]:
    """Create ProjectDEPFiling rows for each selected form.

    Idempotent: skips if a non-dismissed row already exists for (project, form).
    Returns the full list of live rows for the project (both new and pre-existing).
    Caller owns the transaction — no flush or commit inside.
    """
    result = []
    for form_id in form_ids:
        existing = (
            await db.execute(
                select(ProjectDEPFiling).where(
                    ProjectDEPFiling.project_id == project_id,
                    ProjectDEPFiling.dep_filing_form_id == form_id,
                    ProjectDEPFiling.dismissed_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            row = ProjectDEPFiling(
                project_id=project_id,
                dep_filing_form_id=form_id,
                is_saved=False,
                created_by_id=current_user_id,
            )
            db.add(row)
            result.append(row)
        else:
            result.append(existing)

    return result


@register_requirement_type("project_dep_filing", events=[])
class ProjectDEPFilingHandler:
    """Registry handler for Silo 3 DEP filing requirements.

    Materialization is manager-driven (POST /projects/{id}/dep-filings), not event-driven.
    No WA-code trigger involvement; events=[] means dispatch never calls handle_event.
    """

    requirement_type: ClassVar[str] = "project_dep_filing"
    is_dismissable: ClassVar[bool] = True

    @classmethod
    def validate_template_params(cls, params: dict) -> None:
        if params:
            raise ValueError(
                "project_dep_filing triggers are not configurable via requirement-triggers; "
                "materialization is manager-driven"
            )

    @classmethod
    async def handle_event(
        cls, project_id: int, event: RequirementEvent, payload: dict, db: AsyncSession
    ) -> None:
        pass  # No event subscriptions; this handler is never called by the dispatcher

    @classmethod
    async def get_unfulfilled_for_project(
        cls, project_id: int, db: AsyncSession
    ) -> list[ProjectDEPFiling]:
        return list(
            (
                await db.execute(
                    select(ProjectDEPFiling).where(
                        ProjectDEPFiling.project_id == project_id,
                        ProjectDEPFiling.is_saved.is_(False),
                        ProjectDEPFiling.dismissed_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
